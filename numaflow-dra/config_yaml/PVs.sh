# This script creates same PVs of different name.
# When you delete PVs, "kubectl delete pv my-local-pv-{1..4}"

for i in {1..4}; do
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: my-local-pv-$i
spec:
  capacity:
    storage: 3Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/disks/pv$i
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage # change this field according to the Storage Class being used
EOF
done