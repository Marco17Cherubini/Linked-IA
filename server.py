from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route("/exec", methods=["POST"])
def exec_command():
    command = request.json.get("command")
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
        return result
    except subprocess.CalledProcessError as e:
        return e.output, 400

if __name__ == "__main__":
    app.run(debug=True)
