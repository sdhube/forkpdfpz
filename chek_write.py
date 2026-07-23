["bash", "-c", "pdf-suspects-search", filename] 
 result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.stdout:
        print(f"stdout: {result.stdout.strip()}")
    if result.stderr:
        print(f"stderr: {result.stderr.strip()}")
    return result.returncode, result.stdout, result.stderr


error: Failed to parse chek_write.py:1:1: Unexpected indentation
