#!/usr/bin/env python3
import time

from branchy import process


def main():
    with process("Deploy", show_elapsed=True) as deploy:
        deploy.log("resolving target")
        time.sleep(0.3)
        target = deploy.input("Target environment [production]: ") or "production"
        deploy.rename(f"Deploy to {target}")

        with deploy.child("Validate") as v:
            v.log("schema ok")
            time.sleep(0.5)

        with deploy.child("Build", show_elapsed=True) as b:
            with b.child("Compile") as c:
                c.log("gcc -O2 main.c")
                time.sleep(0.4)
            with b.child("Link", show_elapsed=True) as l:
                l.log("ld -o app")
                time.sleep(0.4)

    time.sleep(0.3)

    try:
        with process("Publish", show_elapsed=True) as p:
            p.log("starting upload")
            time.sleep(0.3)

            with p.child("Sign package") as s:
                s.log("private key not found")
                time.sleep(0.3)
                raise RuntimeError("signing failed")
    except RuntimeError as exc:
        print(f"\nExpected failure captured: {exc}")


if __name__ == "__main__":
    main()
