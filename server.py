import tornado
import tornado.ioloop
import contextlib
import os
import uuid
import re
from tornado.web import RequestHandler, stream_request_body, asynchronous, gen
# import tornado.stack_context
import logging
from tornado.options import define, options


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


class UploadFile():

    @gen.coroutine
    def __init__(self, request):
        self.filename = uuid.uuid4().hex
        self.filepath = os.path.join(_UPLOAD_PATH, self.filename)
        try:
            self.content_length = int(request.headers.get('Content-Length'))
        except Exception as e:
            # logging.error('Exception "{0}" occurred while reading header "Content-Length"!'.format(str(e)))
            raise('Exception "{0}" occurred while reading header "Content-Length"!'.format(str(e)))

        self.original_filename = ''
        self.content_type = ''
        self.read_bytes = 0
        self.chunk_number = 0
        self.file = open(self.filepath, 'wb')

    @gen.coroutine
    def write(self, chunk):
        self.file.write(chunk)

    @gen.coroutine
    def close(self):
        self.file.close()


@stream_request_body
class Upload(RequestHandler):

    @gen.coroutine
    def prepare(self):
        filename = uuid.uuid4().hex
        filepath = os.path.join(_UPLOAD_PATH, filename)
        try:
            self.file = open(filepath, 'wb')
        except Exception as e:
            logging.error('Exception "{0}" occurred while opening destination file: "{1}".\n'
                          'Traceback:'
                          .format(str(e)), filepath)
            raise tornado.web.HTTPError(404)
        try:
            self.content_length = int(self.request.headers.get('Content-Length'))
        except Exception as e:
            logging.error('Exception "{0}" occurred while reading header "Content-Length".\n'
                          'Traceback:'
                          .format(str(e)))
            raise tornado.web.HTTPError(404)

        self.original_filename = ''
        self.content_type = ''
        self.read_bytes = 0
        self.chunk_number = 0

        UPLOADS_KEYS[filename] = {'content_length': self.content_length, 'original_filename': self.original_filename,
                                  }

    @gen.coroutine
    def post(self):
        # self.finish()
        print('ok:')
        print(UPLOADS_KEYS)

    @gen.coroutine
    def data_received(self, chunk):
        self.read_bytes += len(chunk)
        self.chunk_number += 1

        if self.chunk_number == 1:
            try:
                chunk = yield self._get_head(chunk)
            except Exception as e:
                logging.error('Exception "{0}" occurred while parsing first chunk.\n'
                              'Readed: {1} bytes.\nTraceback:'
                              .format(str(e), self.read_bytes))
                raise tornado.web.HTTPError(500)

        if self.read_bytes == self.content_length:
            try:
                chunk = yield self._clear_end(chunk)
            except Exception as e:
                logging.error('Exception "{0}" occurred while parsing last chunk.\n'
                              'Readed: {1} bytes.\nTraceback:'
                              .format(str(e), self.read_bytes))
                raise tornado.web.HTTPError(500)
            yield self._finish()

        self.file.write(chunk)

    @gen.coroutine
    def _get_head(self, chunk):
        """
        http://www.w3.org/TR/html401/interact/forms.html#h-17.13.4.2
        https://docs.python.org/3/library/stdtypes.html#bytes.partition
        """
        head_arr = chunk.partition(b'\r\n\r\n')
        name_match = re.match('.* filename="([^"]*)"', str(head_arr[0]))
        self.original_filename = name_match.group(1)
        ct_match = re.match('.*\s*Content-Type: (.*)\'', str(head_arr[0]))
        self.content_type = ct_match.group(1)
        chunk = head_arr[2]  # replace with clean body

        # raise ValueError('Wrong filename!')
        return chunk

    @gen.coroutine
    def _clear_end(self, chunk):
        if self.content_length == self.read_bytes:
            end_arr = chunk[::-1].partition(b'------\n\r')  # reverse for partition()
            chunk = end_arr[2][::-1]  # replace with clean body
        return chunk

    @gen.coroutine
    def _finish(self):
        self.chunk_number = 0
        self.file.close()
        newname = '{}_{}'.format(self.file.name, self.original_filename)
        os.rename(self.file.name, newname)
        msg = 'Uploaded: {} "{}", {} bytes'.format(newname, self.content_type, self.content_length)
        logging.info(msg)
        print(msg)


if __name__ == "__main__":
    app = tornado.web.Application([
        (r"/", UploadForm),
        (r"/upload", Upload),
    ], debug=True)

    opts = tornado.options.parse_command_line()
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
