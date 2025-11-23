from fastapi import APIRouter, Depends, HTTPException, Request
from kubernetes import client
from sqlalchemy.orm import Session

from ..auth import verify_api_key
from ..config import settings
from ..db import get_db
from ..k8s_client import core_v1, apps_v1
from ..logging_utils import safe_log_op
from ..schemas import ScaleRequest

router = APIRouter(dependencies=[Depends(verify_api_key)])


def ensure_ns(namespace: str):
    if namespace not in settings.ALLOWED_NAMESPACES:
        raise HTTPException(status_code=403, detail=f"namespace {namespace} not allowed")


@router.delete("/namespaces/{namespace}/pods/{pod_name}")
def delete_pod(
    namespace: str,
    pod_name: str,
    request: Request,
    db: Session = Depends(get_db),
):
    ensure_ns(namespace)
    status = "error"
    err = None
    try:
        core_v1.delete_namespaced_persistent_volume_claim  # noqa: F401 (preload)
        core_v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        status = "success"
        return {"status": "ok", "action": "delete_pod", "namespace": namespace, "pod": pod_name}
    except client.exceptions.ApiException as e:
        err = e.body
        raise HTTPException(status_code=e.status, detail=e.body)
    finally:
        safe_log_op(
            db,
            request=request,
            action="delete_pod",
            resource_kind="Pod",
            namespace=namespace,
            resource_name=pod_name,
            request_body=None,
            status=status,
            error_message=err,
        )


@router.post("/namespaces/{namespace}/deployments/{name}/scale")
def scale_deployment(
    namespace: str,
    name: str,
    body: ScaleRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ensure_ns(namespace)
    status = "error"
    err = None
    try:
        patch = {"spec": {"replicas": body.replicas}}
        apps_v1.patch_namespaced_deployment(name=name, namespace=namespace, body=patch)
        status = "success"
        return {
            "status": "ok",
            "action": "scale_deployment",
            "namespace": namespace,
            "deployment": name,
            "replicas": body.replicas,
        }
    except client.exceptions.ApiException as e:
        err = e.body
        raise HTTPException(status_code=e.status, detail=e.body)
    finally:
        safe_log_op(
            db,
            request=request,
            action="scale_deployment",
            resource_kind="Deployment",
            namespace=namespace,
            resource_name=name,
            request_body=body.dict(),
            status=status,
            error_message=err,
        )


@router.post("/namespaces/{namespace}/statefulsets/{name}/scale")
def scale_statefulset(
    namespace: str,
    name: str,
    body: ScaleRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ensure_ns(namespace)
    status = "error"
    err = None
    try:
        patch = {"spec": {"replicas": body.replicas}}
        apps_v1.patch_namespaced_stateful_set(name=name, namespace=namespace, body=patch)
        status = "success"
        return {
            "status": "ok",
            "action": "scale_statefulset",
            "namespace": namespace,
            "statefulset": name,
            "replicas": body.replicas,
        }
    except client.exceptions.ApiException as e:
        err = e.body
        raise HTTPException(status_code=e.status, detail=e.body)
    finally:
        safe_log_op(
            db,
            request=request,
            action="scale_statefulset",
            resource_kind="StatefulSet",
            namespace=namespace,
            resource_name=name,
            request_body=body.dict(),
            status=status,
            error_message=err,
        )


@router.delete("/namespaces/{namespace}/persistentvolumeclaims/{pvc_name}")
def delete_pvc(
    namespace: str,
    pvc_name: str,
    request: Request,
    db: Session = Depends(get_db),
):
    ensure_ns(namespace)
    status = "error"
    err = None
    try:
        core_v1.delete_namespaced_persistent_volume_claim(
            name=pvc_name,
            namespace=namespace,
        )
        status = "success"
        return {"status": "ok", "action": "delete_pvc", "namespace": namespace, "pvc": pvc_name}
    except client.exceptions.ApiException as e:
        err = e.body
        raise HTTPException(status_code=e.status, detail=e.body)
    finally:
        safe_log_op(
            db,
            request=request,
            action="delete_pvc",
            resource_kind="PersistentVolumeClaim",
            namespace=namespace,
            resource_name=pvc_name,
            request_body=None,
            status=status,
            error_message=err,
        )
