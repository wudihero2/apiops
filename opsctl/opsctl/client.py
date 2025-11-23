"""
API client for communicating with ApiOps
"""

import requests
from typing import Optional, Dict, Any
from .config import config


class ApiOpsClient:
    """Client for ApiOps API"""

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.api_url = (api_url or config.api_url or "").rstrip('/')
        self.api_key = api_key or config.api_key

        if not self.api_url or not self.api_key:
            raise ValueError(
                "API URL and API Key are required. "
                "Run 'opsctl config set' or set OPSCTL_API_URL and OPSCTL_API_KEY environment variables."
            )

        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
        })

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make HTTP request"""
        url = f"{self.api_url}{path}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("Authentication failed. Check your API key.")
            elif e.response.status_code == 403:
                raise Exception(f"Permission denied: {e.response.text}")
            elif e.response.status_code == 404:
                raise Exception(f"Not found: {path}")
            else:
                raise Exception(f"API error: {e.response.text}")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot connect to {self.api_url}. Is the API server running?")
        except requests.exceptions.Timeout:
            raise Exception("Request timeout")

    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """GET request"""
        response = self._request('GET', path, **kwargs)
        return response.json()

    def post(self, path: str, **kwargs) -> Dict[str, Any]:
        """POST request"""
        response = self._request('POST', path, **kwargs)
        return response.json()

    def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """DELETE request"""
        response = self._request('DELETE', path, **kwargs)
        return response.json()

    # Health check
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        return self.get('/health/live')

    # Atomic operations
    def delete_pod(self, namespace: str, pod_name: str) -> Dict[str, Any]:
        """Delete a pod"""
        return self.delete(f'/ops/namespaces/{namespace}/pods/{pod_name}')

    def delete_pvc(self, namespace: str, pvc_name: str) -> Dict[str, Any]:
        """Delete a PVC"""
        return self.delete(f'/ops/namespaces/{namespace}/persistentvolumeclaims/{pvc_name}')

    def scale_deployment(self, namespace: str, name: str, replicas: int) -> Dict[str, Any]:
        """Scale a deployment"""
        return self.post(
            f'/ops/namespaces/{namespace}/deployments/{name}/scale',
            json={'replicas': replicas}
        )

    def scale_statefulset(self, namespace: str, name: str, replicas: int) -> Dict[str, Any]:
        """Scale a statefulset"""
        return self.post(
            f'/ops/namespaces/{namespace}/statefulsets/{name}/scale',
            json={'replicas': replicas}
        )

    # Job operations
    def create_pg_rebuild_job(
        self,
        namespace: str,
        statefulset: str,
        ordinal: int,
        target_replicas: int = 1,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Create a PG rebuild job"""
        return self.post(
            '/ops/jobs/pg-rebuild',
            json={
                'namespace': namespace,
                'statefulset': statefulset,
                'ordinal': ordinal,
                'target_replicas': target_replicas,
                'max_retries': max_retries,
            }
        )

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get job status"""
        return self.get(f'/ops/jobs/{job_id}')

    def retry_job(self, job_id: str) -> Dict[str, Any]:
        """Manually retry a failed job"""
        return self.post(f'/ops/jobs/{job_id}/retry')
