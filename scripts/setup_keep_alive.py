import os
import subprocess
import sys

def main():
    target_url = "https://quensultingai-voice-agent.onrender.com/health"
    cron_comment = "# QuensultingAI Backend Keep-Alive"
    cron_command = f"*/10 * * * * curl -s {target_url} > /dev/null 2>&1"
    cron_entry = f"{cron_command} {cron_comment}"

    print(f"Setting up keep-alive cron job for: {target_url}")
    print(f"Target cron entry: {cron_entry}")

    try:
        # Retrieve existing crontab
        try:
            current_cron = subprocess.check_output("crontab -l", shell=True, stderr=subprocess.DEVNULL).decode("utf-8")
        except subprocess.CalledProcessError:
            # If no crontab exists yet, initialize as empty
            current_cron = ""

        # Check if the entry already exists
        if target_url in current_cron:
            print("\nKeep-alive cron job already exists in your crontab. Nothing to do!")
            print("Current crontab entries matching target:")
            for line in current_cron.splitlines():
                if target_url in line:
                    print(f"  {line}")
            return

        # Prepare new crontab content
        new_cron = current_cron.strip()
        if new_cron:
            new_cron += "\n"
        new_cron += f"{cron_entry}\n"

        # Write the new crontab
        process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(input=new_cron)

        if process.returncode == 0:
            print("\nSuccess! Keep-alive cron job successfully installed in your crontab.")
            print("It will ping the Render server health check endpoint every 10 minutes to keep it active.")
            print("\nYou can inspect your crontab at any time by running:")
            print("  crontab -l")
        else:
            print(f"\nError installing crontab: {stderr.strip()}", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"\nFailed to set up keep-alive cron job: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
