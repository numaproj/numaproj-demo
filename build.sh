make image IMAGE_NAMESPACE=quay.io/numaio COLOR=blue SLIDER=false IMAGE_TAG=puffy ERROR_RATE=1
docker push quay.io/numaio/numalogic-demo:puffy

make image IMAGE_NAMESPACE=quay.io/numaio COLOR=blue SLIDER=false IMAGE_TAG=puffyerror ERROR_RATE=80
docker push quay.io/numaio/numalogic-demo:puffyerror

make image IMAGE_NAMESPACE=quay.io/numaio COLOR=blue SLIDER=false IMAGE_TAG=puffylatency LATENCY=3
docker push quay.io/numaio/numalogic-demo:puffylatency

make image IMAGE_NAMESPACE=quay.io/numaio COLOR=blue SLIDER=false IMAGE_TAG=puffyerrorlatency LATENCY=3 ERROR_RATE=80
docker push quay.io/numaio/numalogic-demo:puffyerrorlatency

make image IMAGE_NAMESPACE=quay.io/numaio COLOR=yellow SLIDER=false IMAGE_TAG=octo ERROR_RATE=1
docker push quay.io/numaio/numalogic-demo:octo

make image IMAGE_NAMESPACE=quay.io/numaio COLOR=yellow SLIDER=false IMAGE_TAG=octoerror ERROR_RATE=80
docker push quay.io/numaio/numalogic-demo:octoerror

make image IMAGE_NAMESPACE=quay.io/numaio COLOR=yellow SLIDER=false IMAGE_TAG=octolatency LATENCY=3
docker push quay.io/numaio/numalogic-demo:octolatency

make image IMAGE_NAMESPACE=quay.io/numaio COLOR=yellow SLIDER=false IMAGE_TAG=octoerrorlatency LATENCY=3 ERROR_RATE=80
docker push quay.io/numaio/numalogic-demo:octoerrorlatency