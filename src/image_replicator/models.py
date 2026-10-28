"""Strict, ordered contracts shared by Agent, graph and provider adapters."""

from dataclasses import dataclass, field
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

REFERENCE_POLICY = "reference-creative-v1"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Box(StrictModel):
    """Coordinates in the original reference image, normalized to 0..1000."""

    x: Annotated[float, Field(ge=0, le=1000)]
    y: Annotated[float, Field(ge=0, le=1000)]
    width: Annotated[float, Field(gt=0, le=1000)]
    height: Annotated[float, Field(gt=0, le=1000)]

    @model_validator(mode="after")
    def bounds(self):
        if self.x + self.width > 1000 or self.y + self.height > 1000:
            raise ValueError("Text box must stay inside the original image")
        return self


class TextBlock(StrictModel):
    content: Annotated[str, Field(min_length=1)]
    box: Box
    css: str


class TextDescription(StrictModel):
    image_id: str
    texts: list[TextBlock]


class VisualDescription(StrictModel):
    image_id: str
    scene: Annotated[str, Field(min_length=1)]


class TextBatch(StrictModel):
    images: list[TextDescription]


class VisualBatch(StrictModel):
    images: list[VisualDescription]


class SceneObject(StrictModel):
    id: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")]
    description: Annotated[str, Field(min_length=1)]
    count: Annotated[int, Field(ge=1, le=100)]
    placement: Annotated[str, Field(min_length=1)]
    action: Annotated[str, Field(min_length=1)]


class LayoutRegion(StrictModel):
    id: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")]
    purpose: Annotated[str, Field(min_length=1)]
    box: Box


class ProductAttribute(StrictModel):
    """Intrinsic attributes of the featured product, never scene objects or relations."""

    property: Literal[
        "name", "dimensions", "material", "color", "pattern", "texture", "specification"
    ]
    value: Annotated[str, Field(min_length=1)]
    source: Annotated[str, Field(min_length=1)]


class BrandStyle(StrictModel):
    palette: list[Annotated[str, Field(min_length=1)]] | None = None
    text_color: (
        Annotated[
            str,
            Field(
                pattern=r"^#[0-9A-Fa-f]{6}$",
                description="Final foreground "
                "color for structured text blocks, selected by Agent for product/brand theme and "
                "legibility. Replaces reference CSS color while preserving boxes and typography.",
            ),
        ]
        | None
    ) = None
    tone: Annotated[str, Field(min_length=1)] | None = None
    art_style: (
        Annotated[
            str,
            Field(
                min_length=1,
                description="Set only for an explicit user art-style request. Otherwise "
                "omit: preserve each reference's artistic medium even when palette changes.",
            ),
        ]
        | None
    ) = None
    typography: Annotated[str, Field(min_length=1)] | None = None


class DesignOverrides(StrictModel):
    reference_mode: Literal["full"] | None = None
    product_attributes: list[ProductAttribute] | None = None
    brand_style: BrandStyle | None = None
    # Empty legacy fields remain readable; new structural instructions are forbidden.
    objects: Annotated[list[SceneObject], Field(max_length=0)] | None = None
    layout_regions: Annotated[list[LayoutRegion], Field(max_length=0)] | None = None
    forbidden_elements: Annotated[list[str], Field(max_length=0)] | None = None
    checks: list[str] | None = None

    @model_validator(mode="after")
    def unique_attributes(self):
        items = self.product_attributes or []
        if len({item.property for item in items}) != len(items):
            raise ValueError("Product attribute properties must be unique")
        return self


class CopyReplacement(StrictModel):
    old: Annotated[str, Field(min_length=1)]
    new: Annotated[str, Field(min_length=1)]
    source: Annotated[str, Field(min_length=1)]


class Delta(StrictModel):
    # Copy changes retain reference text regions and visual hierarchy.
    texts: list[TextBlock] | None = None
    text_replacements: list[CopyReplacement] | None = None
    scene: (
        Annotated[
            str,
            Field(
                min_length=1,
                description="Product/brand appearance notes only; cannot change composition, "
                "objects, counts, roles, actions or relationships.",
            ),
        ]
        | None
    ) = None
    instruction: Annotated[
        str,
        Field(
            description="Additional product/brand adaptation only. "
            "Never overrides protected reference scene structure.",
        ),
    ] = ""
    design: DesignOverrides | None = None


class ProductFact(StrictModel):
    value: Annotated[str, Field(min_length=1)]
    source: Annotated[str, Field(min_length=1)]


class ProductContext(StrictModel):
    facts: list[ProductFact] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    defaults: Delta = Field(default_factory=Delta)


class ReviewCheck(StrictModel):
    id: str
    verdict: Literal["pass", "fail", "uncertain"]
    evidence: Annotated[str, Field(min_length=1)]


class ReviewReport(StrictModel):
    image_id: str
    artifact_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    design_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    checks: list[ReviewCheck]


class ReferenceReviewReport(ReviewReport):
    reference_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class RevisionUpdate(StrictModel):
    image_id: str
    delta: Delta


class AnalysisRecoveryUpdate(StrictModel):
    image_id: str
    delta: Delta | None = None
    retry_kinds: list[Literal["text", "visual"]] = Field(default_factory=list)
    allow_terminal_http_retry: bool = False

    @model_validator(mode="after")
    def explicit_recovery(self):
        if self.delta is None and not self.retry_kinds:
            raise ValueError("Supply a corrected complete delta or explicit analysis retry kinds")
        if len(set(self.retry_kinds)) != len(self.retry_kinds):
            raise ValueError("Analysis retry kinds must be unique")
        return self


class RunOptions(StrictModel):
    image_model: Literal["gpt-image-2.5-flare", "gpt-image-2.5-sunburst"] = Field(
        default="gpt-image-2.5-flare",
        description="Model family; the prepared canvas selects base (<=1024), -2k (<=2048), "
        "or -4k (<=4096) automatically.",
    )
    concurrency: Annotated[int, Field(ge=1)] | None = None
    selected_image_ids: Annotated[list[str], Field(min_length=1)] | None = None
    review_mode: Literal["manual", "vision"] = "manual"
    max_visual_revisions: Annotated[int, Field(ge=0)] | None = None


@dataclass
class GraphState:
    thread_id: str
    manifest: dict = field(default_factory=dict)
    prepared: list[dict] = field(default_factory=list)
    text_descriptions: list[dict] = field(default_factory=list)
    visual_descriptions: list[dict] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    generated: list[dict] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    designs: list[dict] = field(default_factory=list)
