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

ADD  ui ./
COPY ui ./ui

COPY --from=build /go/src/app/numalogic-demo /numalogic-demo



ARG FISH
ENV FISH=${FISH}
ARG ERROR_RATE
ENV ERROR_RATE=${ERROR_RATE}
ARG LATENCY
ENV LATENCY=${LATENCY}
ARG SLIDER
ENV SLIDER=${SLIDER}

RUN echo "const ENV_${FISH}={\"latency\": \"${LATENCY}\",\"errorRate\": \"${ERROR_RATE}\",\"slider\": \"${SLIDER}\" }" > env.js
ENTRYPOINT [ "/numalogic-demo" ]
