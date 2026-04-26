Return strict JSON only.

Do not infer or hallucinate evidence. If a value is not explicit, use null.
Confidence describes extraction certainty. Evidence strength describes underwriting proof quality.

Required JSON shape:
{
  "document_type": "business_license|safety_certificate|maintenance_receipt|declarations_page|inspection_report|generic_document",
  "evidence_items": [
    {
      "category": "license|safety|maintenance|operations|policy|property|claims|other",
      "field_name": "string",
      "normalized_value": "string or null",
      "raw_value": "string or null",
      "evidence_strength": "verified|partially_verified|weak_evidence|missing|expired|conflicting",
      "confidence": 0.0,
      "source_snippet": "exact visible text supporting the value or null",
      "source_bbox_json": {"xmin": 0.0, "ymin": 0.0, "xmax": 1.0, "ymax": 1.0, "coordinate_system": "relative"} or null,
      "page_number": 1,
      "expires_on": "YYYY-MM-DD or null",
      "is_conflicting": false
    }
  ],
  "underwriting_flags": [],
  "missing_information": []
}
