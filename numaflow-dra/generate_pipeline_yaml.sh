#!/bin/bash

# Read .env file
if [ -f repo.env ]; then
    export $(grep -vE '^\s*#|^\s*$' repo.env | sed 's/\s*#.*$//')
fi

# Convert pipelineXXX.yaml.template into pipelineXXX.yaml
find . -type f -name 'pipeline*.yaml.template' | while read template_file; do
    if [ -f "$template_file" ]; then
        output_file="${template_file%.template}"

        if [ -e "$output_file" ]; then
            echo "Skipping: $output_file already exists."
            continue
        fi

        envsubst < "$template_file" > "$output_file"
        echo "Generated: $output_file"
    fi
done
