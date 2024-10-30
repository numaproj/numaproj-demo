####################################################################################################
# base
####################################################################################################
FROM alpine:3.12.3 AS base
ARG TARGETARCH
RUN apk update && apk upgrade && \
    apk add ca-certificates && \
    apk --no-cache add tzdata

COPY generator/dist/emart-order-gen-${TARGETARCH} /bin/emart-order-gen

RUN chmod +x /bin/emart-order-gen

####################################################################################################
# emart-order-gen
####################################################################################################
FROM scratch AS emart-order-gen
ARG ARCH
COPY --from=base /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=base /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=base /bin/emart-order-gen /bin/emart-order-gen
ENTRYPOINT [ "/bin/emart-order-gen" ]
