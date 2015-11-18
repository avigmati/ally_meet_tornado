import tornado
import tornado.ioloop
import contextlib
import os
import uuid
import re
from tornado.web import RequestHandler, stream_request_body, asynchronous, gen
#
# import tornado.stack_context
#
# Неясно пока для чего эта бандура
#
##############################
import logging
from tornado.options import define, options


_UPLOAD_PATH = './upload'
UPLOAD_KEYS = []
MAX_BUFFER_SIZE = 7813988580 # allowed file size in bytes


class UploadForm(RequestHandler):
    def get(self):
        self.render("upload_form.html")


class UploadFile():

    def __init__(self, request):
        self.request = request
        self.filename = uuid.uuid4().hex
        self.filepath = os.path.join(_UPLOAD_PATH, self.filename)
        self.original_filename = ''
        self.content_type = ''
        self.read_bytes = 0
        self.chunk_number = 0
        self.file = open(self.filepath, 'wb')
        try:
            self.content_length = int(self.request.headers.get('Content-Length'))
        except Exception as e:
            # logging.error('Exception "{0}" occurred while reading header "Content-Length"!'.format(str(e)))
            raise('Exception "{0}" occurred while reading header "Content-Length"!'.format(str(e)))


@stream_request_body
class Upload(RequestHandler):

    @gen.coroutine
    def prepare(self):
        self.file = UploadFile(self.request)
        UPLOAD_KEYS.append(self.file.filename)

    @gen.coroutine
    def post(self):
        # self.finish()
        print('ok:')
        print(UPLOAD_KEYS)

    @gen.coroutine
    def data_received(self, chunk):
        self.file.read_bytes += len(chunk)
        self.file.chunk_number += 1

        if self.file.chunk_number == 1:
            try:
                chunk = yield self._get_head(chunk)
            except Exception as e:
                logging.error('Exception "{0}" occurred while parsing first chunk.\n'
                              'Readed: {1} bytes.\nTraceback:'
                              .format(str(e), self.file.read_bytes))
                raise tornado.web.HTTPError(500)

        if self.file.read_bytes == self.file.content_length:
            try:
                chunk = yield self._clear_end(chunk)

            except Exception as e:
                logging.error('Exception "{0}" occurred while parsing last chunk.\n'
                              'Readed: {1} bytes.\nTraceback:'
                              .format(str(e), self.file.read_bytes))
                raise tornado.web.HTTPError(500)

        self.file.file.write(chunk)

        if self.file.read_bytes == self.file.content_length:
            self.file.chunk_number = 0
            self.file.file.close()
            newname = '{}_{}'.format(self.file.filename, self.file.original_filename)
            os.rename(self.file.filepath, os.path.join(_UPLOAD_PATH, newname))
            msg = 'Uploaded: {} "{}", {} bytes'.format(newname, self.file.content_type, self.file.content_length)
            logging.info(msg)
            print(msg)

    @gen.coroutine
    def _get_head(self, chunk):
        """
        http://www.w3.org/TR/html401/interact/forms.html#h-17.13.4.2
        https://docs.python.org/3/library/stdtypes.html#bytes.partition
        """
        head_arr = chunk.partition(b'\r\n\r\n')
        name_match = re.match('.* filename="([^"]*)"', str(head_arr[0]))
        self.file.original_filename = name_match.group(1)
        ct_match = re.match('.*\s*Content-Type: (.*)\'', str(head_arr[0]))
        self.file.content_type = ct_match.group(1)
        chunk = head_arr[2]  # replace with clean body

        # raise ValueError('Wrong filename!')
        return chunk

    @gen.coroutine
    def _clear_end(self, chunk):
        if self.file.content_length == self.file.read_bytes:
            end_arr = chunk[::-1].partition(b'------\n\r')  # reverse for partition()
            chunk = end_arr[2][::-1]  # replace with clean body
        return chunk


if __name__ == "__main__":
    app = tornado.web.Application([
        (r"/", UploadForm),
        (r"/upload", Upload),
    ], debug=True)

    opts = tornado.options.parse_command_line()
    app.listen(8888, max_buffer_size=MAX_BUFFER_SIZE)
    tornado.ioloop.IOLoop.instance().start()
