from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class AgeGroup(str, Enum):
    """Standardized demographic age-group brackets."""
    UNDER_18 = "<18"
    AGE_18_24 = "18-24"
    AGE_25_34 = "25-34"
    AGE_35_44 = "35-44"
    AGE_45_54 = "45-54"
    AGE_55_PLUS = "55+"
    UNKNOWN = "unknown"


class GenderCategory(str, Enum):
    """Normalized categorical gender representations."""
    FEMALE = "female"
    MALE = "male"
    NON_BINARY = "non_binary"
    OTHER = "other"
    UNKNOWN = "unknown"


class LocationData(BaseModel):
    """Structured location metadata without raw coordinates or IP geolocation."""
    country: Optional[str] = Field(default=None, description="Country name or ISO code")
    region: Optional[str] = Field(default=None, description="State, province, or region name")
    city: Optional[str] = Field(default=None, description="City or municipality name")

    model_config = ConfigDict(from_attributes=True)


class DemographicProfile(BaseModel):
    """
    Optional demographic metadata representation for a user or post.
    Designed for future platform adapters without fabricating non-existent data.
    """
    user_id: Optional[Union[str, int]] = Field(default=None, description="Platform or internal user identifier")
    author_username: Optional[str] = Field(default=None, description="Author handle")
    post_id: Optional[int] = Field(default=None, description="Internal database post ID")
    external_post_id: Optional[str] = Field(default=None, description="External platform post ID")
    age: Optional[int] = Field(default=None, ge=0, le=125, description="Explicit reported age")
    age_group: Optional[AgeGroup] = Field(default=None, description="Pre-bucketed age group")
    gender: Optional[Union[GenderCategory, str]] = Field(default=None, description="Reported or normalized gender")
    location: Optional[Union[LocationData, str]] = Field(default=None, description="Location metadata or string")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional non-PII demographic attributes")

    model_config = ConfigDict(from_attributes=True)


class DemographicBreakdown(BaseModel):
    """
    Statistical aggregate breakdown for a specific demographic dimension.
    """
    counts: Dict[str, int] = Field(default_factory=dict, description="Frequency count per category")
    percentages: Dict[str, float] = Field(default_factory=dict, description="Percentage share per category (0.0 - 100.0)")
    total_known: int = Field(default=0, ge=0, description="Total count with known/explicit metadata")
    total_unknown: int = Field(default=0, ge=0, description="Total count with missing/unknown metadata")
    coverage_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage of records with known data")

    model_config = ConfigDict(from_attributes=True)


class DemographicDistribution(BaseModel):
    """
    Aggregated demographic distributions across all supported dimensions.
    """
    total_records_analyzed: int = Field(..., ge=0, description="Total records/profiles evaluated")
    age_groups: DemographicBreakdown = Field(..., description="Age group distribution")
    gender: DemographicBreakdown = Field(..., description="Gender category distribution")
    countries: DemographicBreakdown = Field(..., description="Country-level distribution")
    regions: DemographicBreakdown = Field(..., description="Region/State distribution")
    cities: DemographicBreakdown = Field(..., description="City-level distribution")

    model_config = ConfigDict(from_attributes=True)


class TopicDemographicResult(BaseModel):
    """Demographic composition associated with a specific extracted topic."""
    topic_id: str = Field(..., description="Unique machine topic ID")
    topic_label: str = Field(..., description="Human-readable topic title")
    post_count: int = Field(..., ge=0, description="Number of posts in topic cluster")
    demographics: DemographicDistribution = Field(..., description="Demographic breakdown for this topic")

    model_config = ConfigDict(from_attributes=True)


class SentimentDemographicResult(BaseModel):
    """Demographic composition associated with a sentiment classification."""
    sentiment_label: str = Field(..., description="Sentiment category (positive, neutral, negative)")
    post_count: int = Field(..., ge=0, description="Number of posts in sentiment class")
    demographics: DemographicDistribution = Field(..., description="Demographic breakdown for this sentiment class")

    model_config = ConfigDict(from_attributes=True)


class TrendDemographicResult(BaseModel):
    """Demographic composition driving a temporal topic trend."""
    topic_id: str = Field(..., description="Unique topic identifier")
    topic_label: str = Field(..., description="Topic label")
    trend_direction: str = Field(..., description="Trend trajectory (emerging, spiking, growing, etc.)")
    growth_rate: float = Field(..., description="Topic percentage growth rate")
    demographics: DemographicDistribution = Field(..., description="Demographic breakdown for this trending topic")

    model_config = ConfigDict(from_attributes=True)


class BatchDemographicResult(BaseModel):
    """
    Aggregated multi-dimensional demographic intelligence report.
    """
    total_profiles_analyzed: int = Field(..., ge=0, description="Total profiles evaluated")
    overall_distribution: DemographicDistribution = Field(..., description="Aggregate demographic distribution")
    topic_breakdowns: List[TopicDemographicResult] = Field(default_factory=list, description="Topic-correlated demographics")
    sentiment_breakdowns: List[SentimentDemographicResult] = Field(default_factory=list, description="Sentiment-correlated demographics")
    trend_breakdowns: List[TrendDemographicResult] = Field(default_factory=list, description="Trend-correlated demographics")
    model: str = Field(..., description="Name and version of the demographic engine used")
    analyzed_at: datetime = Field(..., description="Timestamp of analysis in UTC")

    model_config = ConfigDict(from_attributes=True)
