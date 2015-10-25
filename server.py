import tornado
import tornado.ioloop
import tornado.web
import os


_UPLOAD_PATH = './upload'


class UploadForm(tornado.web.RequestHandler):
    def get(self):
        self.render("upload_form.html")

class Upload(tornado.web.RequestHandler):
    def post(self):
        file = self.request.files['fileobj'][0]
        original_fname = file['filename']
        output_file = open(os.path.join(_UPLOAD_PATH, original_fname), 'wb')
        output_file.write(file.body)
        self.finish("file " + original_fname + " is uploaded!")

app = tornado.web.Application([
    (r"/", UploadForm),
    (r"/upload", Upload),
], debug=True)

def run():
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    run()