"""Strict, ordered contracts shared by Agent, graph and provider adapters."""

from dataclasses import dataclass, field
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    content: Annotated[str, Field(min_length=1, max_length=4000)]
    box: Box
    css: Annotated[str, Field(max_length=2000)]


class TextDescription(StrictModel):
    image_id: str
    texts: list[TextBlock]


class VisualDescription(StrictModel):
    image_id: str
    scene: Annotated[str, Field(min_length=1, max_length=16000)]


class TextBatch(StrictModel):
    images: list[TextDescription]


class VisualBatch(StrictModel):
    images: list[VisualDescription]


class Delta(StrictModel):
    # None means retain the base; [] explicitly removes all reference copy.
    texts: list[TextBlock] | None = None
    scene: Annotated[str, Field(min_length=1, max_length=16000)] | None = None
    instruction: Annotated[str, Field(max_length=16000)] = ""


class RunOptions(StrictModel):
    image_model: Literal["gpt-image-2.5-flare", "gpt-image-2.5-sunburst"] = Field(
        default="gpt-image-2.5-flare",
        description="Model family; the prepared canvas selects base (<=1024), -2k (<=2048), "
        "or -4k (<=4096) automatically.",
    )
    concurrency: Annotated[int, Field(ge=1, le=8)] = 2


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
