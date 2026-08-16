# Mac Pro 1,1 "Omni-Server" Master Plan

**Goal:** Transform the MacPro1,1 into a multi-purpose powerhouse for the `xcelsior` network. This involves a strategic dual-boot setup (Linux + El Capitan) while strictly preserving the existing OS X Lion installation (the "browns" user) untouched.

**Phase 1: Partitioning & Preservation (The Drive Shuffle)**
*   **Objective:** Safely break the RAID array to put Apple OSs on Drive A and dedicate Drive B to Linux, while keeping El Capitan small (150GB).
*   **Execution:** 
    *   Break the AppleRAID mirror, freeing up `disk1`.
    *   Clone the live OS X Lion (`disk0`) over to `disk1` as a temporary liferaft.
    *   Wipe `disk0` completely and partition it: **850 GB Mac OS Lion** and **150 GB El Capitan**.
    *   Clone Lion back from `disk1` onto the 850 GB partition on `disk0`.
    *   Wipe `disk1` completely and dedicate the entire 1 TB drive to the new **Linux Server**.
    *   *Result:* Zero data loss. Disk 0 is purely Apple (Lion + El Capitan). Disk 1 is pure Linux.

**Phase 2: The El Capitan Bootloader Hack**
*   **Objective:** Install a modern OS X to gain access to modern TLS and browsers.
*   **Execution:**
    *   Download the El Capitan installer on the Linux machine.
    *   Use the community `boot.efi` hack (MacPostFactor/Pikify methodology) to bypass the Mac Pro's 32-bit EFI lock.
    *   Deploy the patched installer to a USB drive and boot the Mac Pro holding the Option key.
    *   Install to the new El Capitan partition.

**Phase 3: The 32-bit EFI Linux Installation**
*   **Objective:** Give the Mac Pro a native, lightweight server OS for Docker and Nginx.
*   **Execution:**
    *   Use *Mac Linux USB Loader* to create a hybrid bootable Linux USB.
    *   Install a headless Linux Server distro (like Debian) to the dedicated Linux partition.
    *   Configure the bootloader (GRUB) to allow easy switching between Lion, El Capitan, and Linux.

**Phase 4: Network & Proxy Engineering (The Staging Fix)**
*   *Note: This phase will be executed while booted into the new Linux partition for maximum performance and Docker compatibility.*
*   **Objective:** Turn the Mac Pro into the `xcelsior` network's "Traffic Cop."
*   **Execution:**
    *   **Tailscale:** Install Tailscale and configure the Mac Pro as an Exit Node (`--advertise-exit-node`).
    *   **Stripe Webhook Ingress:** Install `cloudflared` (Cloudflare Tunnels) or Tailscale Funnel. Route incoming public webhooks securely to `192.168.1.127` (the staging Linux machine). *This unblocks the `xcelsior` MVP 2.0 deployment.*
    *   **Nginx Load Balancer:** Install Nginx. Configure local domain routing (e.g., `api.pixelenhance.local` -> `192.168.1.127:8000`) and configure SSL Termination using Let's Encrypt/Certbot.
    *   **Local Caching:** Configure an Nginx caching proxy or Squid to aggressively cache `pip`, `npm`, and `docker pull` requests to save external bandwidth.

**Phase 5: Observability Offloading**
*   **Objective:** Move the heavy monitoring stack off the primary Linux machine.
*   **Execution:**
    *   Use Docker Compose on the Mac Pro's Linux partition to spin up Grafana and Prometheus.
    *   Configure them to scrape metrics from the `xcelsior` and `pixelenhance-labs` nodes across the Tailscale mesh.

**Phase 6: Legacy Optimization (If booted into Lion)**
*   **Objective:** Ensure the legacy partition runs as smoothly as possible when visited.
*   **Execution:**
    *   Execute the `defaults write` commands via the MCP server to disable the Dashboard and window animations.
    *   Ensure the `ai-cockpit` user is configured as the primary automated access point.

---
*This plan represents a massive architectural overhaul. It relies on community-supported EFI hacks and careful disk management.*