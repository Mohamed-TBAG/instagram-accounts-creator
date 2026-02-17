#!/bin/bash

# Usage: ./manage_redroid.sh [create|start|stop|delete|list] [name] [port]
# Example: ./manage_redroid.sh create redroid_test 6610

ACTION=$1
NAME=$2
PORT=$3

if [ -z "$ACTION" ]; then
    echo "Usage: $0 [create|start|stop|delete|list] [container_name] [port]"
    exit 1
fi

if [ "$ACTION" != "list" ] && [ -z "$NAME" ]; then
    echo "Error: Name is required for $ACTION."
    exit 1
fi

case "$ACTION" in
    create)
        if [ -z "$PORT" ]; then
            echo "Error: Port is required for creation."
            exit 1
        fi
        echo "Creating Redroid container '$NAME' on port $PORT..."
        
        # GPU Check
        # GPU Check
        if [ -d "/dev/dri" ]; then
            # Using GID 44 (video) directly to avoid lookup issues in minimal environments
            DEVICE_ARGS+=(--device /dev/dri --group-add 44)
            BOOT_ARGS+=("androidboot.redroid_gpu_mode=host")
            echo "GPU detected. Enabling acceleration (GID 44)."
        else
            BOOT_ARGS+=("androidboot.redroid_gpu_mode=guest")
            echo "No GPU found. Using guest mode."
        fi

        docker run -itd --rm --privileged \
            --name "$NAME" \
            -v /dev/binderfs:/dev/binderfs \
            "${DEVICE_ARGS[@]}" \
            -p "$PORT":5555 \
            redroid/redroid:11.0.0-latest \
            androidboot.redroid_width=720 \
            androidboot.redroid_height=1280 \
            androidboot.redroid_dpi=320 \
            androidboot.use_memfd=1 \
            androidboot.serialno="REDROID$(date +%s)" \
            "${BOOT_ARGS[@]}"
            
        echo "Container '$NAME' created."
        echo "Wait ~30-90s for it to boot, then connect: adb connect localhost:$PORT"
        ;;
        
    start)
        echo "Starting container '$NAME'..."
        docker start "$NAME"
        ;;
        
    stop)
        echo "Stopping container '$NAME'..."
        docker stop "$NAME"
        ;;
        
    delete)
        echo "Deleting container '$NAME'..."
        docker rm -f "$NAME"
        ;;

    list)
        echo "Listing all redroid containers..."
        docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -iE "NAME|redRED"
        ;;
        
    *)
        echo "Invalid action: $ACTION"
        echo "Usage: create, start, stop, delete, list"
        exit 1
        ;;
esac