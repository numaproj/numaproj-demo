####################################################################################################
# base
####################################################################################################
FROM alpine:3.12.3 AS base
ARG TARGETARCH
RUN apk update && apk upgrade && \
    apk add ca-certificates && \
    apk --no-cache add tzdata

COPY dist/emart-${TARGETARCH} /bin/emart

RUN chmod +x /bin/emart

####################################################################################################
# emart
####################################################################################################
FROM scratch AS emart
ARG ARCH
COPY --from=base /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=base /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=base /bin/emart /bin/emart
ENTRYPOINT [ "/bin/emart" ]
