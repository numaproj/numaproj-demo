FROM golang:1.18 as build
WORKDIR /go/src/app
COPY . .
RUN make

FROM alpine
COPY *.html ./
COPY *.png ./
COPY *.js ./
COPY *.ico ./
COPY *.css ./
COPY images1/* ./

COPY --from=build /go/src/app/numalogic-demo /numalogic-demo



ARG COLOR
ENV COLOR=${COLOR}
ARG ERROR_RATE
ENV ERROR_RATE=${ERROR_RATE}
ARG LATENCY
ENV LATENCY=${LATENCY}
ARG SLIDER
ENV SLIDER=${SLIDER}

RUN echo "const ENV_${COLOR}={\"latency\": \"${LATENCY}\",\"errorRate\": \"${ERROR_RATE}\",\"slider\": \"${SLIDER}\" }" > env.js
ENTRYPOINT [ "/numalogic-demo" ]
