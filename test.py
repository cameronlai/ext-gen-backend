from flask import Flask, request
from main import http

app = Flask(__name__)

@app.route('/extgen', methods=['POST'])
def main():
    return http(request)    

if __name__ == '__main__':
    app.run(debug=True)