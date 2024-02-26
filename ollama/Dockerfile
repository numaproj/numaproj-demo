####################################################################################################
# base
####################################################################################################
FROM alpine:3.12.3 as base
RUN apk update && apk upgrade && \
    apk add ca-certificates && \
    apk --no-cache add tzdata

COPY dist/ollama-cli /bin/ollama-cli
RUN chmod +x /bin/ollama-cli

####################################################################################################
# ollama-cli
####################################################################################################
FROM scratch as ollama-cli
ARG ARCH
COPY --from=base /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=base /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=base /bin/ollama-cli /bin/ollama-cli
ENTRYPOINT [ "/bin/ollama-cli" ]
