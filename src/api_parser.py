#!/usr/bin/env python3
"""
Parse captured network traffic to reconstruct API endpoints
"""

import json
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

load_dotenv()


class APIEndpointReconstructor:
    def __init__(self, captured_data_file: str):
        self.captured_data_file = captured_data_file
        self.api_calls = self.load_captured_data()
        self.endpoints = {}
        self.graphql_operations = {}

    def load_captured_data(self) -> List[Dict[str, Any]]:
        """Load captured API calls from JSON file"""
        try:
            with open(self.captured_data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"File {self.captured_data_file} not found")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return []

    def parse_api_calls(self):
        """Parse captured API calls to reconstruct endpoints"""
        print(f"📊 Parsing {len(self.api_calls)} captured API calls...")

        for call in self.api_calls:
            if call["type"] == "request":
                self.analyze_request(call)

        self.generate_reconstruction_report()

    def analyze_request(self, request: Dict[str, Any]):
        """Analyze individual request to extract API information"""
        url = request["url"]
        method = request["method"]
        headers = request.get("headers", {})
        post_data = request.get("post_data")

        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # Check if this looks like a GoWish/Onskeskyen API call
        if self.is_relevant_api_call(url):
            endpoint_key = f"{method} {path}"

            if endpoint_key not in self.endpoints:
                self.endpoints[endpoint_key] = {
                    "method": method,
                    "path": path,
                    "domain": domain,
                    "full_url": url,
                    "headers": {},
                    "query_params": query_params,
                    "examples": [],
                }

            # Collect headers (excluding sensitive ones)
            safe_headers = self.filter_safe_headers(headers)
            self.endpoints[endpoint_key]["headers"].update(safe_headers)

            # Store example request
            example = {
                "timestamp": request["timestamp"],
                "url": url,
                "post_data": post_data,
            }
            self.endpoints[endpoint_key]["examples"].append(example)

            # Special handling for GraphQL endpoints
            if "graphql" in path.lower() and post_data:
                self.analyze_graphql_operation(post_data, request["timestamp"])

    def is_relevant_api_call(self, url: str) -> bool:
        """Check if URL is a relevant API call to capture"""
        relevant_patterns = [
            "api.gowish.com",
            "auth.gowish.com",
            "onskeskyen.dk/api",
            "graphql",
            "oauth",
            "token",
            "login",
            "auth",
        ]
        return any(pattern in url.lower() for pattern in relevant_patterns)

    def filter_safe_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Filter out sensitive headers"""
        sensitive_headers = {
            "authorization",
            "cookie",
            "set-cookie",
            "x-csrf-token",
            "x-api-key",
            "x-auth-token",
        }
        return {k: v for k, v in headers.items() if k.lower() not in sensitive_headers}

    def analyze_graphql_operation(self, post_data: str, timestamp: str):
        """Analyze GraphQL operations"""
        try:
            if post_data.startswith('{"'):
                # JSON payload
                data = json.loads(post_data)
                if "query" in data:
                    operation = self.extract_graphql_operation_name(data["query"])
                    if operation:
                        if operation not in self.graphql_operations:
                            self.graphql_operations[operation] = {
                                "query": data["query"],
                                "variables_examples": [],
                                "timestamps": [],
                            }

                        self.graphql_operations[operation]["variables_examples"].append(
                            data.get("variables", {})
                        )
                        self.graphql_operations[operation]["timestamps"].append(
                            timestamp
                        )
        except json.JSONDecodeError:
            pass

    def extract_graphql_operation_name(self, query: str) -> str:
        """Extract operation name from GraphQL query"""
        query = query.strip()
        if query.startswith("query"):
            # Extract query name
            lines = query.split("\n")
            first_line = lines[0].strip()
            if " " in first_line:
                parts = first_line.split()
                if len(parts) > 1:
                    return parts[1].split("(")[0].split("{")[0].strip()
            return "UnnamedQuery"
        elif query.startswith("mutation"):
            lines = query.split("\n")
            first_line = lines[0].strip()
            if " " in first_line:
                parts = first_line.split()
                if len(parts) > 1:
                    return parts[1].split("(")[0].split("{")[0].strip()
            return "UnnamedMutation"
        return "UnknownOperation"

    def generate_reconstruction_report(self):
        """Generate a comprehensive report of discovered API endpoints"""
        print("\n🔍 API Reconstruction Report")
        print("=" * 50)

        print(f"\n📡 Discovered {len(self.endpoints)} API endpoints:")
        for endpoint_key, details in self.endpoints.items():
            print(f"\n• {endpoint_key}")
            print(f"  Domain: {details['domain']}")
            print(f"  Full URL: {details['full_url']}")
            print(f"  Examples: {len(details['examples'])}")

            if details["query_params"]:
                print(f"  Query Params: {list(details['query_params'].keys())}")

            # Show common headers
            common_headers = list(details["headers"].keys())[:5]
            if common_headers:
                print(f"  Headers: {', '.join(common_headers)}")

        if self.graphql_operations:
            print(f"\n🔮 GraphQL Operations ({len(self.graphql_operations)}):")
            for operation_name, details in self.graphql_operations.items():
                print(f"\n• {operation_name}")
                print(f"  Called: {len(details['timestamps'])} times")

                # Show query (truncated)
                query = details["query"].replace("\n", " ").strip()
                if len(query) > 100:
                    query = query[:97] + "..."
                print(f"  Query: {query}")

        # Save detailed reconstruction
        self.save_reconstruction_data()

    def save_reconstruction_data(self):
        """Save reconstructed API data to files"""
        # Save endpoint summary
        endpoint_summary = {
            "endpoints": self.endpoints,
            "graphql_operations": self.graphql_operations,
            "summary": {
                "total_endpoints": len(self.endpoints),
                "total_graphql_operations": len(self.graphql_operations),
                "domains": list(set(ep["domain"] for ep in self.endpoints.values())),
            },
        }

        with open("api_reconstruction_report.json", "w", encoding="utf-8") as f:
            json.dump(endpoint_summary, f, indent=2, ensure_ascii=False)

        print("\n💾 Saved detailed reconstruction to api_reconstruction_report.json")

        # Generate Python client template
        self.generate_client_template()

    def generate_client_template(self):
        """Generate a Python client template based on discovered APIs"""
        template = '''#!/usr/bin/env python3
"""
Reconstructed GoWish/Onskeskyen API Client
Generated from network traffic analysis
"""

import requests
from typing import Dict, Any, Optional
import json


class ReconstructedAPIClient:
    def __init__(self, session_cookies: Optional[Dict[str, str]] = None):
        self.session = requests.Session()

        if session_cookies:
            self.session.cookies.update(session_cookies)

'''

        # Add methods for each discovered endpoint
        for endpoint_key, details in self.endpoints.items():
            method_name = self.generate_method_name(endpoint_key, details)
            template += f"""    def {method_name}(self"""

            if details["method"] == "POST":
                template += ", data: Optional[Dict[str, Any]] = None"

            template += f''') -> Dict[str, Any]:
        """
        {endpoint_key}
        Domain: {details["domain"]}
        """
        url = "{details["full_url"].split("?")[0]}"
        '''

            if details["method"] == "GET":
                template += """
        response = self.session.get(url)
        """
            elif details["method"] == "POST":
                template += """
        response = self.session.post(url, json=data)
        """

            template += """response.raise_for_status()
        return response.json()

"""

        # Add GraphQL methods
        if self.graphql_operations:
            template += '''    def graphql_request(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute GraphQL query"""
        # You'll need to determine the correct GraphQL endpoint from captured traffic
        graphql_url = "https://api.gowish.com/graphql"  # Update this based on captured data

        payload = {
            "query": query,
            "variables": variables or {}
        }

        response = self.session.post(graphql_url, json=payload)
        response.raise_for_status()
        return response.json()

'''

            for operation_name, details in self.graphql_operations.items():
                method_name = f"graphql_{operation_name.lower()}"
                template += f'''    def {method_name}(self, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        GraphQL {operation_name}
        """
        query = """{details["query"]}"""

        return self.graphql_request(query, variables)

'''

        template += """

# Example usage:
if __name__ == "__main__":
    # You'll need to provide session cookies from a logged-in browser session
    # These can be extracted from browser dev tools after logging in
    session_cookies = {
        # Add your session cookies here
    }

    client = ReconstructedAPIClient(session_cookies)

    # Example API calls based on discovered endpoints
    try:
        # Add example calls based on your discovered endpoints
        pass
    except Exception as e:
        print(f"Error: {e}")
"""

        with open("reconstructed_api_client.py", "w", encoding="utf-8") as f:
            f.write(template)

        print("💾 Generated Python client template: reconstructed_api_client.py")

    def generate_method_name(self, endpoint_key: str, details: Dict[str, Any]) -> str:
        """Generate a Python method name from endpoint details"""
        method, path = endpoint_key.split(" ", 1)

        # Extract meaningful parts from path
        path_parts = [
            part for part in path.split("/") if part and not part.startswith("{")
        ]

        if not path_parts:
            return f"{method.lower()}_request"

        # Create method name
        method_name = f"{method.lower()}_{'_'.join(path_parts)}"

        # Clean up method name
        method_name = method_name.replace("-", "_").replace(".", "_")

        return method_name


def main():
    """Main function to run API reconstruction"""
    import sys

    if len(sys.argv) > 1:
        captured_file = sys.argv[1]
    else:
        # Look for the most recent captured file
        captured_files = list(Path(".").glob("captured_api_calls_*.json"))
        if captured_files:
            captured_file = str(max(captured_files, key=lambda p: p.stat().st_mtime))
            print(f"Using most recent captured file: {captured_file}")
        else:
            print("No captured API files found. Run network_monitor.py first.")
            return

    reconstructor = APIEndpointReconstructor(captured_file)
    reconstructor.parse_api_calls()


if __name__ == "__main__":
    main()
