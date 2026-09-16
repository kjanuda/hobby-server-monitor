import pylxd


def main():
    client = pylxd.Client()

    print("Connected to LXD successfully.")

    containers = client.containers.all()

    if not containers:
        print("No containers found.")
        return

    print("\nContainers:")

    for container in containers:
        print(f"- {container.name} | status: {container.status}")


if __name__ == "__main__":
    main()