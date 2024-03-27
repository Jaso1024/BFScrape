from pydantic import BaseModel, Field
from typing import List, Optional

class LinkDecision(BaseModel):
    url: str = Field(..., description="The URL of the link candidate.")
    reason: Optional[str] = Field(None, description="Optional reason or notes for the model's decision.")

class LinkSelectionOutput(BaseModel):
    links_to_search: List[LinkDecision] = Field(..., description="List of links the model has chosen to search.")
    links_to_ignore: Optional[List[LinkDecision]] = Field(None, description="List of links the model has chosen to ignore, with reasons if available.")
    model_notes: Optional[str] = Field(None, description="Any additional notes or rationale from the model about the selection process.")

class LinkAssessment(BaseModel):
    url: str = Field(..., description="The URL of the link candidate.")
    should_traverse: bool = Field(..., description="True if the model thinks this link is potentially relevant and should be considered for traversal, False otherwise.")
    rank: int = Field(..., description="The rank assigned by the model (lower is higher priority) among the links marked should_traverse=True.")
    reason: Optional[str] = Field(None, description="Optional reason or notes for the model's assessment.")

class LinkAssessmentOutput(BaseModel):
    assessed_links: List[LinkAssessment] = Field(..., description="List of links assessed by the model, with traversal decisions and ranks.")
    model_notes: Optional[str] = Field(None, description="Any additional notes or rationale from the model about the assessment process.") 