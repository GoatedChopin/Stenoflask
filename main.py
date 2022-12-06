import os
from datetime import datetime
from storage import upload_blob, upload_blob_from_memory
import audio
from flask import Flask, request, jsonify, make_response
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = os.path.join(os.environ["pwd"], "audio_uploads")
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = os.environ["stenobug_secret_key"]
ALLOWED_EXTENSIONS = {"wav", "m4a", "mp3"}


@app.route("/")
def hello_world():
    name = os.environ.get("NAME", "World")
    return "Hello {}!".format(name)


def allowed_file(filename):
    if '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
        return True
    else:
        return False


#  curl -X POST -F file=@/home/colby/Documents/pyjects/stenobug/whisper_test.m4a 'http://localhost:5000/whisper'
@app.route('/whisper_archive', methods=['POST'])
def upload_file():
    # check if the post request has the file part
    if 'file' not in request.files:
        data = {'message': 'No selected file', 'code': 'FAILURE'}
        return make_response(jsonify(data), 403)
    
    file = request.files['file']

    if file.filename == '':
        data = {'message': 'Empty filename', 'code': 'FAILURE'}
        return make_response(jsonify(data), 403)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        timestamp = str(datetime.now()).replace(" ", "_")

        # Send the file to google cloud storage
        upload_blob("inbound-audio", os.path.join(app.config['UPLOAD_FOLDER'], filename), timestamp + "." + filename.rsplit('.', 1)[1].lower())

        # Transcribe the file to text
        text_transcription = audio.transcribe(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Send transcription to google cloud storage
        upload_blob_from_memory("outbound-text", text_transcription, timestamp + ".txt")

        data = {'message': 'Done', 'code': 'SUCCESS'}
        return make_response(jsonify(data), 200) 

    data = {'message': 'Done', 'code': 'FAILURE'}
    return make_response(jsonify(data), 403)



#  curl -X POST -H "text/plain" -d {cat whisper_test.m4a} 'http://localhost:5000/whisper'
@app.route('/whisper', methods=['POST'])
def whisper_endpoint(): 

    data = request.data

    if not data:
        response = {'message': 'Empty audio', 'code': 'FAILURE'}
        return make_response(jsonify(response), 403)

    if data:
        filename = "recording.wav"
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "wb") as file:
            file.write(request.data)

        timestamp = str(datetime.now()).replace(" ", "_")

        # Send the file to google cloud storage
        upload_blob("inbound-audio", os.path.join(app.config['UPLOAD_FOLDER'], filename), timestamp + "." + filename.rsplit('.', 1)[1].lower())

        # Transcribe the file to text
        text_transcription = audio.transcribe(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Send transcription to google cloud storage
        upload_blob_from_memory("outbound-text", text_transcription, timestamp + ".txt")

        response = {'message': 'Done', 'code': 'SUCCESS'}
        return make_response(jsonify(response), 200) 

    response = {'message': 'Done', 'code': 'FAILURE'}
    return make_response(jsonify(response), 403)



@app.route('/echo', methods=['POST'])
def echo():
    out = ""
    filename = "recording.wav"
    if request.data:
        print(request.data)
        # return request.data
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "wb") as file:
            file.write(request.data)

        text_transcription = audio.transcribe(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        out += text_transcription    

        print(out)
    return out


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))