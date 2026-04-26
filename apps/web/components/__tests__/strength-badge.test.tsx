import React from "react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { StrengthBadge } from "@/components/strength-badge";

describe("StrengthBadge", () => {
  it("renders a human-readable evidence strength", () => {
    render(<StrengthBadge strength="weak_evidence" />);
    expect(screen.getByText("weak evidence")).toBeInTheDocument();
  });
});
