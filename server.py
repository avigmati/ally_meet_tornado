import tornado
import tornado.ioloop
import os
import uuid
import re
from tornado.web import RequestHandler, stream_request_body, gen
#
# import contextlib
# import tornado.stack_context
#
# Неясно пока для чего эта бандура
#
##############################
import logging
from tornado.options import define, options

define('upload_path', default='./upload', help='Upload path')
define('port', default=8888, help='Listen on this port')
define('max_buffer_size', default=1024*1024*1024*9, help='Max allowed file size in bytes')

UPLOAD_KEYS = {}  # {'filename': UploadFile obj}

class UploadFile():

    def __init__(self, request):
        self.request = request
        self.filename = uuid.uuid4().hex
        self.filepath = os.path.join(options.upload_path, self.filename)
        self.original_filename = ''
        self.content_type = ''
        self.read_bytes = 0
        self.chunk_number = 0
        self.file = open(self.filepath, 'wb')

        self.client_key = self.request.query_arguments.get('key', None)
        if not self.client_key:
            raise('No "key" (GET) parameter!')
        else:
            self.client_key = self.client_key[0]
            print(self.client_key)

        try:
            self.content_length = int(self.request.headers.get('Content-Length'))
        except Exception as e:
            raise('Exception "{0}" occurred while read header "Content-Length"!'.format(str(e)))

    @gen.coroutine
    def percentages(self):
        return int(round(self.read_bytes / self.content_length, 2) * 100)


class UploadForm(RequestHandler):

    @gen.coroutine
    def get(self):
        self.render("upload_form.html")


class UploadPercentages(RequestHandler):

    @gen.coroutine
    def get(self):
        try:
            client_key = str(self.get_argument('key'))
            file = UPLOAD_KEYS.get(client_key, None)
            p = yield file.percentages() if file else ''
            self.write('{}%'.format(p))
        except Exception as e:
            raise('Exception "{0}" occurred while get file upload percentages!'.format(str(e)))


@stream_request_body
class Upload(RequestHandler):

    @gen.coroutine
    def prepare(self):
        try:
            self.file = UploadFile(self.request)
        except Exception as e:
            raise tornado.web.HTTPError(500)
        UPLOAD_KEYS[self.file.client_key] = self.file

    @gen.coroutine
    def post(self):
        print('ok:')
        print(UPLOAD_KEYS)
        self.write('{}'.format(UPLOAD_KEYS))

    @gen.coroutine
    def data_received(self, chunk):
        self.file.read_bytes += len(chunk)
        self.file.chunk_number += 1

        if self.file.chunk_number == 1:
            try:
                chunk = yield self._get_head(chunk)
            except Exception as e:
                logging.error('Exception "{0}" occurred while parse first chunk.\n'
                              'Readed: {1} bytes.\nTraceback:'
                              .format(str(e), self.file.read_bytes))
                raise tornado.web.HTTPError(500)

        if self.file.read_bytes == self.file.content_length:
            try:
                chunk = yield self._clear_end(chunk)

            except Exception as e:
                logging.error('Exception "{0}" occurred while parse last chunk.\n'
                              'Readed: {1} bytes.\nTraceback:'
                              .format(str(e), self.file.read_bytes))
                raise tornado.web.HTTPError(500)

        self.file.file.write(chunk)

        if self.file.read_bytes == self.file.content_length:
            self.file.chunk_number = 0
            self.file.file.close()
            newname = '{}_{}'.format(self.file.filename, self.file.original_filename)
            os.rename(self.file.filepath, os.path.join(options.upload_path, newname))
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
        (r"/upload_stat", UploadPercentages),
    ], debug=True)

    options.parse_command_line()
    app.listen(options.port, max_buffer_size=options.max_buffer_size)
    tornado.ioloop.IOLoop.instance().start()
