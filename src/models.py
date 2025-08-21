#!/usr/bin/env python3
"""
Pydantic models for the Onskeskyen API Gateway
Defines request/response schemas and data validation
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, validator, HttpUrl


class ErrorResponse(BaseModel):
    """Standard error response model"""

    success: bool = False
    error: str
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class UserProfile(BaseModel):
    """User profile information"""

    id: str
    email: str
    first_name: str
    last_name: str
    language_code: str
    country_code: str
    profile_image: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "UserProfile":
        """Create UserProfile from API response data"""
        # Handle both error responses and successful responses
        if data.get("data"):
            me_data = data["data"].get("me", {})
        else:
            me_data = data.get("me", {})

        return cls(
            id=me_data.get("id", ""),
            email=me_data.get("email", ""),
            first_name=me_data.get("firstName", ""),
            last_name=me_data.get("lastName", ""),
            language_code=me_data.get("languageCode", ""),
            country_code=me_data.get("countryCode", ""),
            profile_image=me_data.get("profileImage"),
            is_active=me_data.get("isActive", True),
        )


class WishlistOwner(BaseModel):
    """Wishlist owner information"""

    id: str
    first_name: str
    last_name: str
    profile_image: Optional[str] = None


class WishlistCollaborator(BaseModel):
    """Wishlist collaborator information"""

    id: str
    first_name: str
    collaboration_status: str


class WishlistItem(BaseModel):
    """Individual wishlist item"""

    id: str
    title: str
    description: Optional[str] = None
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    quantity: int = 1
    url: Optional[str] = None
    redirect_url: Optional[str] = None
    photos: List[str] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)
    index: Optional[int] = None
    updated_at: Optional[datetime] = None
    purchased: bool = False

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "WishlistItem":
        """Create WishlistItem from API response data"""
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description"),
            price=Decimal(str(data["price"])) if data.get("price") else None,
            currency=data.get("currency"),
            quantity=data.get("quantity", 1),
            url=data.get("url"),
            redirect_url=data.get("redirectUrl"),
            photos=data.get("photos", []),
            labels=data.get("labels", []),
            index=data.get("index"),
            updated_at=datetime.fromisoformat(data["updatedAt"].replace("Z", "+00:00"))
            if data.get("updatedAt")
            else None,
            purchased=data.get("iPurchasedIt", False),
        )


class Wishlist(BaseModel):
    """Wishlist information"""

    id: str
    title: str
    description: Optional[str] = None
    access_level: str
    event_type: Optional[str] = None
    cover_photo: Optional[str] = None
    owner: WishlistOwner
    wishes_count: int = 0
    collaborators_count: int = 0
    followers_count: int = 0
    archived: bool = False
    expires: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    new_updates: bool = False

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Wishlist":
        """Create Wishlist from API response data"""
        owner_data = data.get("owner", {})
        owner = WishlistOwner(
            id=owner_data.get("id", ""),
            first_name=owner_data.get("firstName", ""),
            last_name=owner_data.get("lastName", ""),
            profile_image=owner_data.get("profileImage"),
        )

        wishes_data = data.get("wishes", {})
        collaborators_data = data.get("collaborators", {})
        followers_data = data.get("followers", {})

        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description"),
            access_level=data.get("accessLevel", ""),
            event_type=data.get("eventType"),
            cover_photo=data.get("coverPhoto"),
            owner=owner,
            wishes_count=wishes_data.get("totalCount", 0),
            collaborators_count=collaborators_data.get("totalCount", 0),
            followers_count=followers_data.get("totalCount", 0),
            archived=data.get("archived", False),
            expires=datetime.fromisoformat(data["expires"].replace("Z", "+00:00"))
            if data.get("expires")
            else None,
            last_updated_at=datetime.fromisoformat(
                data["lastUpdatedAt"].replace("Z", "+00:00")
            )
            if data.get("lastUpdatedAt")
            else None,
            new_updates=data.get("newUpdates", False),
        )


class AddWishlistItemRequest(BaseModel):
    """Request model for adding an item to a wishlist"""

    url: HttpUrl = Field(..., description="Product URL to add to wishlist")
    title: Optional[str] = Field(
        None, max_length=200, description="Optional custom title (overrides URL metadata)"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Optional description (overrides URL metadata)"
    )
    price: Optional[Decimal] = Field(None, ge=0, description="Optional price (overrides URL metadata)")
    quantity: int = Field(default=1, ge=1, le=100, description="Quantity (default: 1)")
    use_url_metadata: bool = Field(
        default=True, description="Whether to fetch metadata from URL (default: True)"
    )

    @validator("url")
    def validate_url(cls, v):
        """Validate that URL is accessible"""
        # Convert pydantic HttpUrl to string for processing
        url_str = str(v)
        if not url_str.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return url_str


class AddWishlistItemResponse(BaseModel):
    """Response model for adding an item to a wishlist"""

    success: bool
    message: str
    item: Optional[WishlistItem] = None


class DeleteWishlistItemRequest(BaseModel):
    """Request model for deleting an item from a wishlist"""

    reason: Optional[str] = Field(
        None, max_length=500, description="Optional reason for deletion"
    )


class WishlistsResponse(BaseModel):
    """Response model for getting wishlists"""

    wishlists: List[Wishlist]
    total_count: Optional[int] = None
    next_cursor: Optional[int] = None
    has_more: bool = False


class WishlistItemsResponse(BaseModel):
    """Response model for getting wishlist items"""

    items: List[WishlistItem]
    total_count: Optional[int] = None
    next_cursor: Optional[int] = None
    has_more: bool = False
