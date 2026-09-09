import pytest
from pydantic import ValidationError

from app.schemas.intelligence import (
    DemoPostInput,
    DemoAnalyzePostsRequest,
    DemoContextMode,
    DemoProvenance,
)

def test_demo_post_input_basic():
    """Test basic validation and aliasing for a single post."""
    data = {
        "text": "This is a test post.",
        "author": "tester",
        "likes": 5,
        "comments": 2
    }
    post = DemoPostInput(**data)
    
    assert post.text == "This is a test post."
    assert post.author_handle == "tester"
    assert post.likes == 5
    assert post.replies == 2
    assert post.platform == "X"
    assert post.external_post_id is None # No id provided, should be None in schema (generator handles defaults on payload conversion)
    
def test_demo_post_input_x_v2_alias():
    """Test mapping from X API v2 style data."""
    data = {
        "text": "X v2 style post",
        "author": {
            "username": "x_user",
            "id": "12345"
        },
        "public_metrics": {
            "like_count": 10,
            "retweet_count": 5,
            "reply_count": 1,
            "impression_count": 100
        },
        "id": "999888"
    }
    
    post = DemoPostInput(**data)
    
    assert post.text == "X v2 style post"
    assert post.author_handle == "x_user"
    assert post.author_id == "12345"
    assert post.external_post_id == "999888"
    assert post.likes == 10
    assert post.reposts == 5
    assert post.replies == 1
    assert post.views == 100

def test_demo_post_input_validation_errors():
    """Test validation errors for empty text and text length > 2000."""
    with pytest.raises(ValidationError) as exc_info:
        DemoPostInput(text="   ", author="tester")
    assert "text must not be empty" in str(exc_info.value)
    
    with pytest.raises(ValidationError) as exc_info:
        DemoPostInput(text="A" * 2001, author="tester")
    assert "at most 2000 characters" in str(exc_info.value)

def test_demo_post_input_to_raw_post_payload():
    """Test conversion to RawPostPayload."""
    post = DemoPostInput(
        text="Sample text",
        author="my_handle",
        likes=10,
        comments=2
    )
    raw_payload = post.to_raw_post_payload()
    
    assert raw_payload.text == "Sample text"
    assert raw_payload.author_username == "my_handle"
    assert raw_payload.platform == "X"
    assert raw_payload.metrics.likes == 10
    assert raw_payload.metrics.comments == 2
    
    # Check provenance injected correctly
    assert raw_payload.metadata.get("is_user_seed") is True
    assert raw_payload.metadata.get("provenance") == DemoProvenance.USER_SUPPLIED.value
    assert raw_payload.external_id.startswith("demo_")

def test_demo_analyze_posts_request():
    """Test batch limits 1-50."""
    valid_post = DemoPostInput(text="Sample", author="me")
    
    # 1 post (valid)
    req_single = DemoAnalyzePostsRequest(posts=[valid_post])
    assert len(req_single.posts) == 1
    
    # 50 posts (valid)
    req_max = DemoAnalyzePostsRequest(posts=[valid_post] * 50)
    assert len(req_max.posts) == 50
    
    # 0 posts (invalid)
    with pytest.raises(ValidationError) as exc_info:
        DemoAnalyzePostsRequest(posts=[])
    assert "List should have at least 1 item" in str(exc_info.value)
    
    # 51 posts (invalid)
    with pytest.raises(ValidationError) as exc_info:
        DemoAnalyzePostsRequest(posts=[valid_post] * 51)
    assert "List should have at most 50 items" in str(exc_info.value)
