#!/usr/bin/env python3
"""
Tests for GraphQL client component
"""

import pytest
from unittest.mock import AsyncMock
from src.graphql_client import GraphQLClient


class TestGraphQLClient:
    """Test the GraphQL client functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_page = AsyncMock()
        self.client = GraphQLClient(self.mock_page)

    async def test_execute_query_success(self):
        """Test successful GraphQL query execution"""
        # Arrange
        query = "query { me { id name } }"
        variables = {"limit": 10}
        expected_response = {
            "status": 200,
            "data": {"me": {"id": "123", "name": "Test User"}},
            "headers": {},
            "usedAuthToken": True,
        }
        self.mock_page.evaluate.return_value = expected_response

        # Act
        result = await self.client.execute_query(query, variables)

        # Assert
        assert result == {"me": {"id": "123", "name": "Test User"}}
        self.mock_page.evaluate.assert_called_once()

        # Verify the JavaScript code and payload were passed correctly
        call_args = self.mock_page.evaluate.call_args
        assert query in str(call_args)
        assert "variables" in str(call_args)

    async def test_execute_query_with_none_variables(self):
        """Test GraphQL query execution with None variables"""
        # Arrange
        query = "query { me { id } }"
        expected_response = {
            "status": 200,
            "data": {"me": {"id": "123"}},
            "headers": {},
            "usedAuthToken": False,
        }
        self.mock_page.evaluate.return_value = expected_response

        # Act
        result = await self.client.execute_query(query, None)

        # Assert
        assert result == {"me": {"id": "123"}}

    async def test_execute_query_authentication_expired(self):
        """Test handling of authentication expiration"""
        # Arrange
        query = "query { me { id } }"
        auth_error_response = {
            "status": 401,
            "error": "Unauthorized",
        }
        self.mock_page.evaluate.return_value = auth_error_response

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await self.client.execute_query(query)

        assert "Authentication expired" in str(exc_info.value)

    async def test_execute_query_forbidden_error(self):
        """Test handling of forbidden error"""
        # Arrange
        query = "query { me { id } }"
        forbidden_response = {
            "status": 403,
            "error": "Forbidden",
        }
        self.mock_page.evaluate.return_value = forbidden_response

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await self.client.execute_query(query)

        assert "Authentication expired" in str(exc_info.value)

    async def test_execute_query_server_error(self):
        """Test handling of server errors"""
        # Arrange
        query = "query { me { id } }"
        server_error_response = {
            "status": 500,
            "error": "Internal Server Error",
        }
        self.mock_page.evaluate.return_value = server_error_response

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await self.client.execute_query(query)

        assert "GraphQL request failed with status 500" in str(exc_info.value)
        assert "Internal Server Error" in str(exc_info.value)

    async def test_execute_query_no_page(self):
        """Test handling when no page is available"""
        # Arrange
        client_no_page = GraphQLClient(None)
        query = "query { me { id } }"

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await client_no_page.execute_query(query)

        assert "No page available" in str(exc_info.value)

    async def test_execute_query_javascript_error(self):
        """Test handling of JavaScript execution errors"""
        # Arrange
        query = "query { me { id } }"
        js_error_response = {
            "status": 500,
            "error": "JavaScript execution failed",
        }
        self.mock_page.evaluate.return_value = js_error_response

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await self.client.execute_query(query)

        assert "GraphQL request failed with status 500" in str(exc_info.value)

    async def test_execute_query_empty_response_data(self):
        """Test handling when response data is missing"""
        # Arrange
        query = "query { me { id } }"
        empty_response = {
            "status": 200,
            # No 'data' field
        }
        self.mock_page.evaluate.return_value = empty_response

        # Act
        result = await self.client.execute_query(query)

        # Assert
        assert result == {}  # Should return empty dict when no data field

    async def test_execute_query_with_auth_token(self):
        """Test that auth token is properly used when available"""
        # Arrange
        query = "query { me { id } }"
        expected_response = {
            "status": 200,
            "data": {"me": {"id": "123"}},
            "headers": {},
            "usedAuthToken": True,  # This indicates token was found and used
        }
        self.mock_page.evaluate.return_value = expected_response

        # Act
        result = await self.client.execute_query(query)

        # Assert
        assert result == {"me": {"id": "123"}}
        # Verify the evaluate method was called with the correct JavaScript
        self.mock_page.evaluate.assert_called_once()
        call_args = self.mock_page.evaluate.call_args
        js_code = call_args[0][0]

        # Check that the JavaScript includes auth token handling
        assert "localStorage.getItem('authToken')" in js_code
        assert "Authorization" in js_code
