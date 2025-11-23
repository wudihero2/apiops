from kubernetes import client, config

# 在 cluster 內跑，用 in-cluster config
config.load_incluster_config()

core_v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
