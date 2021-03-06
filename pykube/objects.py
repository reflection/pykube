import copy
import json
import time

import jsonpatch

from .exceptions import ObjectDoesNotExist
from .query import ObjectManager


DEFAULT_NAMESPACE = "default"


class APIObject(object):

    objects = ObjectManager()
    base = None
    namespace = None

    def __init__(self, api, obj):
        self.api = api
        self.set_obj(obj)

    def set_obj(self, obj):
        self.obj = obj
        self._original_obj = copy.deepcopy(obj)

    @property
    def name(self):
        return self.obj["metadata"]["name"]

    @property
    def annotations(self):
        return self.obj["metadata"].get("annotations", {})

    def api_kwargs(self, **kwargs):
        kw = {}
        collection = kwargs.pop("collection", False)
        if collection:
            kw["url"] = self.endpoint
        else:
            kw["url"] = "{}/{}".format(self.endpoint, self._original_obj["metadata"]["name"])
        if self.base:
            kw["base"] = self.base
        kw["version"] = self.version
        if self.namespace is not None:
            kw["namespace"] = self.namespace
        kw.update(kwargs)
        return kw

    def exists(self, ensure=False):
        r = self.api.get(**self.api_kwargs())
        if r.status_code not in {200, 404}:
            self.api.raise_for_status(r)
        if not r.ok:
            if ensure:
                raise ObjectDoesNotExist("{} does not exist.".format(self.name))
            else:
                return False
        return True

    def create(self):
        r = self.api.post(**self.api_kwargs(data=json.dumps(self.obj), collection=True))
        self.api.raise_for_status(r)
        self.set_obj(r.json())

    def reload(self):
        r = self.api.get(**self.api_kwargs())
        self.api.raise_for_status(r)
        self.set_obj(r.json())

    def update(self):
        patch = jsonpatch.make_patch(self._original_obj, self.obj)
        r = self.api.patch(**self.api_kwargs(
            headers={"Content-Type": "application/json-patch+json"},
            data=str(patch),
        ))
        self.api.raise_for_status(r)
        self.set_obj(r.json())

    def delete(self):
        r = self.api.delete(**self.api_kwargs())
        if r.status_code != 404:
            self.api.raise_for_status(r)


class NamespacedAPIObject(APIObject):

    objects = ObjectManager(namespace=DEFAULT_NAMESPACE)

    @property
    def namespace(self):
        if self.obj["metadata"].get("namespace"):
            return self.obj["metadata"]["namespace"]
        else:
            return DEFAULT_NAMESPACE


class ReplicatedAPIObject(object):

    @property
    def replicas(self):
        return self.obj["spec"]["replicas"]

    @replicas.setter
    def replicas(self, value):
        self.obj["spec"]["replicas"] = value


class ConfigMap(NamespacedAPIObject):

    version = "v1"
    endpoint = "configmaps"


class DaemonSet(NamespacedAPIObject):

    version = "extensions/v1beta1"
    endpoint = "daemonsets"


class Deployment(NamespacedAPIObject, ReplicatedAPIObject):

    version = "extensions/v1beta1"
    endpoint = "deployments"


class Endpoint(NamespacedAPIObject):

    version = "v1"
    endpoint = "endpoints"


class Ingress(NamespacedAPIObject):

    version = "extensions/v1beta1"
    endpoint = "ingresses"


class Job(NamespacedAPIObject):

    version = "extensions/v1beta1"
    endpoint = "jobs"


class Namespace(APIObject):

    version = "v1"
    endpoint = "namespaces"


class Node(APIObject):

    version = "v1"
    endpoint = "nodes"


class Pod(NamespacedAPIObject):

    version = "v1"
    endpoint = "pods"

    @property
    def ready(self):
        cs = self.obj["status"]["conditions"]
        condition = next((c for c in cs if c["type"] == "Ready"), None)
        return condition is not None and condition["status"] == "True"


class ReplicationController(NamespacedAPIObject, ReplicatedAPIObject):

    version = "v1"
    endpoint = "replicationcontrollers"

    def scale(self, replicas=None):
        if replicas is None:
            replicas = self.replicas
        self.exists(ensure=True)
        self.replicas = replicas
        self.update()
        while True:
            self.reload()
            if self.replicas == replicas:
                break
            time.sleep(1)


class Secret(NamespacedAPIObject):

    version = "v1"
    endpoint = "secrets"


class Service(NamespacedAPIObject):

    version = "v1"
    endpoint = "services"


class PersistentVolume(APIObject):

    version = "v1"
    endpoint = "persistentvolumes"


class PersistentVolumeClaim(NamespacedAPIObject):

    version = "v1"
    endpoint = "persistentvolumeclaims"
