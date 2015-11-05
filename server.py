import tornado
import tornado.ioloop
# import tornado.web
import os
import uuid
import re
from tornado.web import RequestHandler, stream_request_body, asynchronous

_UPLOAD_PATH = './upload'
UPLOADS_KEYS = {}

def _run_once(f):
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            return f(*args, **kwargs)
    wrapper.has_run = False
    return wrapper

class UploadForm(RequestHandler):
    def get(self):
        self.render("upload_form.html")


@stream_request_body
class Upload(RequestHandler):

    def prepare(self):
        self.file = open(os.path.join(_UPLOAD_PATH, uuid.uuid4().hex), 'wb')
        self.content_length = self.request.headers.get('Content-Length')
        self.original_filename = ''
        self.content_type = ''
        self.read_bytes = 0
        self.chunk_number = 0

    def post(self):
        print(self.file.name, self.original_filename, self.content_type)
        self.finish()

    def data_received(self, chunk):
        self.read_bytes += len(chunk)
        self.chunk_number += 1

        if self.read_bytes > 0:
            try:
                chunk = self._get_head(chunk)
            except ValueError as e:
                print(str(e))
        else:
            raise ValueError

        self.file.write(chunk)

        if self.content_length == self.read_bytes:
            self.chunk_number = 0
            self.file.close()

    @asynchronous
    def _get_head(self, chunk):
        if self.chunk_number == 1:
            ########
            # GET original filename
            #   куда возвращается эксепшн?
            ########
            head_l = chunk.partition(b'\r\n\r\n')  # delimiter of body and form bound data
            if not head_l[-1]:  # subbytes not found
                # https://docs.python.org/3/library/stdtypes.html#bytes.partition
                raise ValueError

            chunk = head_l[2]  # replace with body

            try:
                name_match = re.match('.* filename="([^"]*)"', str(head_l[0]))
                if not name_match:
                    raise ValueError
                if not len(name_match.group(1)):
                    raise ValueError
                self.original_filename = name_match.group(1)
            except Exception as e:
                print('Error: ', str(e))

            ########
            # GET content-type
            ########
            try:
                ct_match = re.match('.*\s*Content-Type: (.*)\'', str(head_l[0]))
                if not ct_match:
                    raise ValueError
                if not len(ct_match.group(1)):
                    raise ValueError
                self.content_type = ct_match.group(1)
            except Exception as e:
                print('Error: ', str(e))

        return chunk


app = tornado.web.Application([
    (r"/", UploadForm),
    (r"/upload", Upload),
], debug=True)


def run():
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    run()