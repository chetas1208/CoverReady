#!/usr/bin/env python3
"""Load the CoverReady synthetic dataset into the database.

Usage:
    python scripts/load_dataset.py [--dataset-dir DIR] [--batch-size N] [--score]

This script reads every JSON document from the dataset, groups them by
workspace_id, and creates the corresponding database rows:
  - BusinessProfile & Workspace (one per workspace_id)
  - Document, DocumentPage, DocumentAsset (per document)
  - EvidenceItem (per ground-truth evidence)
  - OCRRun, ExtractionRun (per document)

Optionally, it can also trigger scorecard recalculation for each workspace
with the --score flag.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

# Make sure we can import the API modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from sqlalchemy import delete, update  # noqa: E402

from coverready_api import models  # noqa: E402
from coverready_api.config.settings import Settings, get_settings  # noqa: E402
from coverready_api.db import Base, build_engine, build_session_maker, init_db  # noqa: E402


# ---------------------------------------------------------------------------
# Field-name mapping: map dataset field_names to fields that the scoring
# engine recognizes via the taxonomy rulesets.
# ---------------------------------------------------------------------------
FIELD_NAME_MAP: dict[str, str] = {
    # License / identity
    "license_status": "license.current",
    "license_number": "license.number",
    "license_expiry": "license.current",
    "business_name": "business.name",
    "business_address": "business.address",
    "owner_name": "business.owner",
    # Safety
    "fire_inspection_result": "safety.fire_inspection.current",
    "fire_inspection_date": "safety.fire_inspection.current",
    "fire_inspection_expiry": "safety.fire_inspection.current",
    "sprinkler_status": "safety.suppression_service.current",
    "sprinkler_service_date": "safety.suppression_service.current",
    "sprinkler_last_service": "safety.suppression_service.current",
    "sprinkler_vendor": "safety.suppression_service.current",
    "extinguisher_status": "safety.extinguisher.current",
    "extinguisher_service_date": "safety.extinguisher.current",
    "fire_extinguisher_visible": "safety.extinguisher.current",
    # Maintenance
    "hood_cleaning_date": "safety.hood_cleaning.current",
    "hood_cleaning_vendor": "safety.hood_cleaning.current",
    "kitchen_exhaust_cleaned": "safety.hood_cleaning.current",
    # Operations
    "training_type": "operations.training.current",
    "training_date": "operations.training.current",
    "training_participants": "operations.training.current",
    "training_count": "operations.training.current",
    "incident_description": "operations.questionnaire.complete",
    "incident_date": "operations.questionnaire.complete",
    "incident_corrective_action": "operations.questionnaire.complete",
    "email_summary": "operations.questionnaire.complete",
    # Policy / coverage
    "policy_number": "policy.current",
    "policy_effective_date": "policy.current",
    "policy_expiration_date": "policy.current",
    "policy_carrier": "policy.current",
    "gl_limit": "coverage.equipment_values.current",
    "property_limit": "coverage.equipment_values.current",
    "deductible": "coverage.equipment_values.current",
    "named_insured": "business.name",
    # Property / occupancy
    "lease_tenant": "occupancy.proof",
    "lease_start_date": "occupancy.proof",
    "lease_end_date": "occupancy.proof",
    "lease_address": "business.address",
    "signage_visible": "business.address",
    "address_visible": "business.address",
    # Renewal
    "loss_history": "renewal.loss_history.current",
    "claims_count": "renewal.loss_history.current",
    "renewal_date": "renewal.policy_expiration.known",
}

# Map dataset document_type to our model's document_type
DOC_TYPE_MAP: dict[str, str] = {
    "business_license": "business_license",
    "fire_inspection_report": "fire_safety_record",
    "sprinkler_service_receipt": "maintenance_receipt",
    "hood_cleaning_certificate": "maintenance_receipt",
    "safety_training_log": "training_record",
    "policy_declarations_page": "declarations_page",
    "lease_excerpt": "lease",
    "incident_log": "operations_questionnaire",
    "property_photo_ocr": "storefront_photo",
    "renewal_email": "operations_questionnaire",
}


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_date(val: str | None) -> date | None:
    if not val:
        return None
    try:
        return date.fromisoformat(val[:10])
    except (ValueError, TypeError):
        return None


def state_from_address(address: str | None) -> str | None:
    """Extract a 2-letter state code from a typical US address string."""
    if not address:
        return None
    parts = address.split(",")
    if len(parts) >= 3:
        state_zip = parts[-1].strip().split()
        if state_zip and len(state_zip[0]) == 2:
            return state_zip[0].upper()
    # Try second-to-last
    if len(parts) >= 2:
        state_zip = parts[-1].strip().split()
        if state_zip and len(state_zip[0]) == 2:
            return state_zip[0].upper()
    return None


def map_field_name(raw_field_name: str) -> str:
    """Map a dataset field_name to a scoring-compatible field identifier."""
    mapped = FIELD_NAME_MAP.get(raw_field_name)
    if mapped:
        return mapped
    # Fallback: use category.field_name as a dotted path
    return raw_field_name


def load_docs(dataset_dir: Path) -> list[dict]:
    """Load all document JSON files from the dataset docs/ directory."""
    docs_dir = dataset_dir / "docs"
    if not docs_dir.exists():
        raise FileNotFoundError(f"Dataset docs directory not found: {docs_dir}")

    doc_files = sorted(docs_dir.glob("COV-*.json"))
    print(f"Found {len(doc_files)} document files in {docs_dir}")

    documents = []
    for fp in doc_files:
        try:
            documents.append(json.loads(fp.read_text()))
        except (json.JSONDecodeError, IOError) as exc:
            print(f"  Warning: skipping {fp.name}: {exc}")
    return documents


def group_by_workspace(documents: list[dict]) -> dict[str, list[dict]]:
    """Group documents by workspace_id."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for doc in documents:
        groups[doc["workspace_id"]].append(doc)
    return dict(groups)


def clear_existing_data(session) -> None:
    """Clear all existing data from the database."""
    print("Clearing existing data...")
    session.execute(update(models.Document).values(latest_job_id=None))
    for model in (
        models.ManualReviewEvent,
        models.ClaimEvidenceLink,
        models.Claim,
        models.MissingRequirement,
        models.ScoreReasonItem,
        models.Scorecard,
        models.EvidenceItem,
        models.ExtractionRun,
        models.OCRRun,
        models.DocumentAsset,
        models.DocumentPage,
        models.ProcessingJob,
        models.Document,
        models.ScenarioRun,
        models.TranslatorRun,
        models.BrokerPacket,
        models.AppSetting,
        models.Workspace,
        models.BusinessProfile,
    ):
        session.execute(delete(model))
    session.commit()
    print("  Done.")


def seed_workspace(session, workspace_id: str, docs: list[dict]) -> str:
    """Create a workspace and its business profile, documents, evidence, etc."""
    # Use the first document's business_profile data for workspace metadata
    first_doc = docs[0]
    bp = first_doc["business_profile"]
    business_name = bp["business_name"]
    address = bp["address"]
    industry_key = bp.get("industry_key", "general")
    state = state_from_address(address)

    # Map certain dataset industry keys to what the scoring engine supports
    industry_code = industry_key
    if industry_key in ("cafe", "bakery", "bar", "food_truck"):
        industry_code = "restaurant"

    business_id = workspace_id

    # Create BusinessProfile
    session.add(models.BusinessProfile(
        id=business_id,
        name=business_name,
        address=address,
        industry_code=industry_code,
        state=state,
        origin="live",
    ))

    # Create Workspace
    session.add(models.Workspace(
        id=workspace_id,
        name=business_name,
        address=address,
        industry_code=industry_code,
        state=state,
        origin="live",
    ))
    session.flush()

    evidence_counter = 0

    for raw_doc in docs:
        doc_id = raw_doc["document_id"]
        doc_type = DOC_TYPE_MAP.get(raw_doc["document_type"], "generic_document")

        # Extract dates from evidence if available
        doc_date = parse_date(raw_doc.get("uploaded_at"))
        expiration_date = None

        # Create Document
        document = models.Document(
            id=doc_id,
            business_profile_id=business_id,
            workspace_id=workspace_id,
            document_type=doc_type,
            status="processed",
            processing_status="processed",
            origin="live",
            source_filename=raw_doc.get("file_name", f"{doc_id}.pdf"),
            mime_type=raw_doc.get("mime_type", "application/pdf"),
            checksum=f"syn-{doc_id}",
            summary=_build_summary(raw_doc),
            document_date=doc_date,
            expiration_date=expiration_date,
        )
        session.add(document)
        session.flush()

        # Create DocumentPages and DocumentAssets from pages
        for page in raw_doc.get("pages", []):
            page_num = page.get("page_number", 1)
            raw_text = page.get("raw_text", "")

            session.add(models.DocumentPage(
                document_id=doc_id,
                page_number=page_num,
                text_content=raw_text,
            ))

            session.add(models.DocumentAsset(
                document_id=doc_id,
                asset_type="page",
                page_number=page_num,
                text_content=raw_text,
                preview_label=f"{raw_doc['document_type'].replace('_', ' ').title()} p{page_num}",
            ))

        # Create OCRRun
        full_text = "\n\n".join(p.get("raw_text", "") for p in raw_doc.get("pages", []))
        session.add(models.OCRRun(
            document_id=doc_id,
            provider="synthetic-dataset",
            status="completed",
            extracted_text=full_text or None,
        ))

        # Create ExtractionRun
        session.add(models.ExtractionRun(
            document_id=doc_id,
            provider="synthetic-dataset",
            status="completed",
            raw_response=raw_doc.get("ground_truth", {}),
        ))

        # Create EvidenceItems from ground_truth
        gt = raw_doc.get("ground_truth", {})
        for ev in gt.get("evidence_items", []):
            ev_id = f"ev-{doc_id}-{evidence_counter}"
            evidence_counter += 1

            raw_field = ev.get("field_name", "unknown")
            mapped_field = map_field_name(raw_field)
            category = ev.get("category", "other")
            strength = ev.get("evidence_strength", "verified")
            confidence = ev.get("confidence", 0.85)
            snippet = ev.get("source_snippet", "")
            page_num = ev.get("page_number", 1)
            normalized_val = ev.get("normalized_value", "")
            raw_val = ev.get("raw_value", normalized_val)

            # Try to extract expiration from normalized_value if it looks like a date
            expires_on = None
            if normalized_val and strength in ("verified", "partially_verified"):
                expires_on = _infer_expiration(raw_doc, ev)

            session.add(models.EvidenceItem(
                id=ev_id,
                business_profile_id=business_id,
                workspace_id=workspace_id,
                document_id=doc_id,
                category=category,
                field=mapped_field,
                field_name=mapped_field,
                value=normalized_val or raw_val,
                normalized_value=normalized_val,
                raw_value=raw_val,
                evidence_strength=strength,
                confidence=confidence,
                source_snippet=snippet,
                page_ref=f"p{page_num}",
                page_number=page_num,
                expires_on=expires_on,
                is_conflicting=False,
                status="active",
                review_status="pending_review",
            ))

    return business_id


def _build_summary(raw_doc: dict) -> str:
    """Build a document summary from the raw document data."""
    doc_type = raw_doc.get("document_type", "document").replace("_", " ").title()
    bp = raw_doc.get("business_profile", {})
    name = bp.get("business_name", "Unknown")
    return f"{doc_type} for {name}."


def _infer_expiration(raw_doc: dict, ev: dict) -> date | None:
    """Try to infer expiration date for specific field types."""
    field = ev.get("field_name", "")
    norm_val = ev.get("normalized_value", "")

    # For license expiry, policy expiration, lease end dates
    if field in ("license_expiry", "policy_expiration_date", "lease_end_date",
                 "fire_inspection_expiry", "sprinkler_service_date"):
        return parse_date(norm_val)

    return None


def run_scoring(session, settings: Settings, business_profile_ids: list[str]) -> None:
    """Recalculate scorecards for all workspaces."""
    from coverready_api.services.scoring import recalculate_scorecard

    print(f"\nCalculating scorecards for {len(business_profile_ids)} workspaces...")
    scored = 0
    errors = 0
    for bp_id in business_profile_ids:
        try:
            recalculate_scorecard(session, settings, bp_id)
            scored += 1
        except Exception as exc:
            errors += 1
            if errors <= 5:
                print(f"  Warning: scoring failed for {bp_id}: {exc}")
    print(f"  Scored {scored}/{len(business_profile_ids)} workspaces ({errors} errors)")


def main():
    parser = argparse.ArgumentParser(description="Load CoverReady synthetic dataset")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "coverready_synthetic_dataset",
        help="Path to the extracted dataset directory",
    )
    parser.add_argument("--batch-size", type=int, default=50, help="Commit every N workspaces")
    parser.add_argument("--score", action="store_true", default=True, help="Recalculate scorecards after loading")
    parser.add_argument("--no-score", dest="score", action="store_false", help="Skip scorecard recalculation")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of workspaces to load (0 = all)")
    args = parser.parse_args()

    print("=" * 60)
    print("CoverReady Dataset Loader")
    print("=" * 60)

    settings = get_settings()
    engine = build_engine(settings)
    session_maker = build_session_maker(engine)
    init_db(engine)

    print(f"Database: {settings.database_url}")
    print(f"Dataset:  {args.dataset_dir}")

    # Load and group documents
    documents = load_docs(args.dataset_dir)
    workspace_groups = group_by_workspace(documents)
    print(f"Found {len(workspace_groups)} unique workspaces across {len(documents)} documents")

    if args.limit > 0:
        workspace_ids = sorted(workspace_groups.keys())[:args.limit]
        workspace_groups = {k: workspace_groups[k] for k in workspace_ids}
        print(f"Limiting to {len(workspace_groups)} workspaces")

    session = session_maker()
    try:
        clear_existing_data(session)

        business_profile_ids = []
        start = time.time()
        workspace_items = sorted(workspace_groups.items())

        for idx, (ws_id, docs) in enumerate(workspace_items, 1):
            bp_id = seed_workspace(session, ws_id, docs)
            business_profile_ids.append(bp_id)

            if idx % args.batch_size == 0:
                session.commit()
                elapsed = time.time() - start
                rate = idx / elapsed
                print(f"  Loaded {idx}/{len(workspace_items)} workspaces "
                      f"({len(docs)} docs) [{rate:.1f} ws/s]")

        # Final commit
        session.commit()
        elapsed = time.time() - start
        total_evidence = sum(
            len(doc.get("ground_truth", {}).get("evidence_items", []))
            for docs in workspace_groups.values()
            for doc in docs
        )
        print(f"\nLoaded {len(workspace_items)} workspaces, "
              f"{len(documents)} documents, "
              f"~{total_evidence} evidence items in {elapsed:.1f}s")

        # Store workspace mode
        session.add(models.AppSetting(key="workspace_mode", value_json={"mode": "dataset"}))
        session.commit()

        # Run scoring
        if args.score:
            run_scoring(session, settings, business_profile_ids)

        print("\n✅ Dataset loaded successfully!")
        print(f"   First workspace ID: {business_profile_ids[0] if business_profile_ids else 'N/A'}")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
