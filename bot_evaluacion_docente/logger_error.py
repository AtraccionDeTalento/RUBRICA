import traceback
def log_error(e):
    with open("error_log.txt", "a", encoding="utf-8") as f:
        f.write(traceback.format_exc() + "\n")
