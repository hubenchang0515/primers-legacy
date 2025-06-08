import os
import re
import stat
import shutil
import subprocess
import mistune
import base64
import hashlib
from datetime import datetime, timezone
from pygments import highlight
import pygments
from pygments.lexers import get_lexer_by_name
from pygments.formatters import html
from urllib.parse import quote
from jinja2 import Template

PRIMERS_DOMAIN:str = "http://primers.cn"
PRIMERS_PREFIX:str = ""

DOCUMENT_DIR:str = "primers-document/document/zh"
RESOURCE_DIR:str = "primers-document/resource"

SHIFT_URL:str = "https://xplanc.org/shift/index.html"

def file_title(filename) -> str:
    items:list[str] = filename.split(".")
    if len(items) == 0:
        return "未命名"
    elif len(items) == 1:
        return items[0]
    elif len(items) == 2:
        return items[1]
    else:
        return ".".join(items[1:-1])

class MarkdownRenderer(mistune.HTMLRenderer):
    '''
    Markdown 渲染器
    '''

    def __init__(self, prefix:str, escape=True, allow_harmful_protocols=None):
        super().__init__(escape, allow_harmful_protocols)
        self.__CURRENT_FILE = File(__file__)
        self.__CURRENT_DIR = File(self.__CURRENT_FILE.dirpath())
        self.__PREFIX = prefix

    def heading(self, text:str, level, **attrs):
        _id = hashlib.sha256(text.encode('utf-8')).hexdigest()[:6]
        if level < 4:
            return f"<h{level} id='{_id}' class='view-h{level+3}'><a class='view-text-miku' href='#{_id}'>#</a> {text}</h{level}>"
        else:

            return f"<h{level} id='{_id}' class='view-p view-strong'><a class='view-text-miku' href='#{_id}'>#</a> {text}</h{level}>"
    
    def paragraph(self, text):
        if text.startswith('!class:'):
            lines:list[str] = text.splitlines()
            classList = lines[0][len('!class:'):]
            content = '\n'.join(lines[1:])
            return f"<div class='custom {classList}'>{content}</div>"
        else:
            return f"<p class='view-p'>{text}</p>"
    
    def link(self, text, url, title=None):
        if url.startswith('/document/zh'):
            items = url.removeprefix('/document/zh').split('/')
            items = map(lambda x:file_title(x), items)
            url = '/document' + '/'.join(items) + '.html'
            return f"<a class='view-text-primary' href='{url}'>{text}</a>"
        if title:
            return f"<a class='view-text-primary' title='{title}' href='{url}' target='_blank'>{text}</a>"
        else:
            return f"<a class='view-text-primary' href='{url}' target='_blank'>{text}</a>"
    
    def block_quote(self, text):
        if ('custom' in text):
            return text
        else:
            return f"<blockquote>{text}</blockquote>"

    def list(self, text, ordered, **attrs):
        if ordered:
            return f"<ol>{text}</ol>"
        else:
            return f"<ul>{text}</ul>"
        
    def list_item(self, text):
        return f"<li><p>{text}</p></li>"
        
    def table(self, text):
        return f"<table class='view-width-100'>{text}</table>"

    def image(self, text, url, title=None):
        if url.startswith("/") and not url.startswith(self.__PREFIX):
            wrapUrl = f"{self.__PREFIX}/{url[1:]}"
            return f"<img class='view-dark-filter' src='{wrapUrl}' alt='{text}' title={title}>"

        return f"<img class='view-dark-filter' src='{url}' alt='{text}' title={title}>"
    
    def codespan(self, text):
        text = text.replace("&amp;", "&")
        return f"<code class='view-text-secondary view-border-1 view-border-secondary'>{text}</code>"
    
    def block_code(self, code, info=None):
        formatter = html.HtmlFormatter(style='nord')
        if not info:
            lexer = get_lexer_by_name('text', stripall=True)
            return f"<div class='view-monofont'>{highlight(code, lexer, formatter)}</div>"
        
        infos = info.split(" ")
        
        # 普通代码
        if len(infos) < 2:
            try:
                lexer = get_lexer_by_name(infos[0], stripall=True)
            except pygments.util.ClassNotFound:
                lexer = get_lexer_by_name('text', stripall=True)
            return f"<div class='view-monofont'>{highlight(code, lexer, formatter)}</div>"
        # 嵌入代码
        elif infos[1] == 'embed':
            return code
        # 删除特殊
        elif infos[1] in ['iframe', 'shift', 'graphviz', 'mermaid']:  
            try:
                lexer = get_lexer_by_name(infos[0], stripall=True)
            except pygments.util.ClassNotFound:
                lexer = get_lexer_by_name('text', stripall=True)
            return f"<div class='view-monofont'>{highlight(code, lexer, formatter)}</div>"
        # iframe
        elif infos[1] == 'iframe':
            return f"<iframe srcdoc='{code.replace("\"", "\\\"")}' style='width:100%;background:#fafafa;'/>"
        # 使用 shift 运行代码
        elif infos[1] == 'shift':
            lexer = get_lexer_by_name(infos[0], stripall=True)
            b64code:str = base64.b64encode(quote(code).encode('utf-8')).decode('utf-8')
            if len(infos) > 2:
                b64input:str = base64.b64encode(quote(infos[2]).encode('utf-8')).decode('utf-8')
                return f"<div class='view-overlap-container' style='height:600px'><div class='view-overlap-layer view-monofont'>{highlight(code, lexer, formatter)}</div><iframe class='view-overlap-layer' loading='lazy' title='代码运行环境' src='{SHIFT_URL}#lang={infos[0]}&input={b64input}&code={b64code}'></iframe></div>"
            else:
                return f"<div class='view-overlap-container' style='height:600px'><div class='view-overlap-layer view-monofont'>{highlight(code, lexer, formatter)}</div><iframe class='view-overlap-layer' loading='lazy' loading='lazy' title='代码运行环境' src='{SHIFT_URL}#lang={infos[0]}&code={b64code}'></iframe></div>"
        else:
            try:
                lexer = get_lexer_by_name(infos[0], stripall=True)
            except pygments.util.ClassNotFound:
                lexer = get_lexer_by_name('text', stripall=True)
            return f"<div class='view-monofont'>{highlight(code, lexer, formatter)}</div>"

class File(object):
    '''
    文件路径处理
    '''

    def __init__(self, path:str) -> None:
        self.__path = os.path.abspath(path)

    def path(self) -> str:
        return self.__path
    
    def filename(self) -> str:
        return os.path.basename(self.__path)
    
    def basename(self) -> str:
        return os.path.splitext(self.filename())[0]
    
    def dirpath(self) -> str:
        return os.path.dirname(self.__path)
    
    def join(self, *subs:str) -> 'File':
        subs = [x.strip("/") for x in subs]
        return File(os.path.join(self.__path, *subs))
    
    def listdir(self,key:None=None) -> list[str]:
        files:list[str] = os.listdir(self.__path)
        files.sort(key=key)
        return files
    
    def exists(self) -> bool:
        return os.path.exists(self.__path)
    
    def isdir(self) -> bool:
        return os.path.isdir(self.__path)

    def remove(self) -> None:
        if not self.exists():
            return
        elif not self.isdir():
            os.chmod(self.__path, stat.S_IRWXU)
            os.remove(self.__path)
        else:
            for filename in self.listdir():
                self.join(filename).remove()
            os.chmod(self.__path, stat.S_IRWXU)
            os.rmdir(self.__path)
    
    def open(self, mode:str="r", encoding="utf-8"):
        if not os.path.exists(self.dirpath()):
            os.makedirs(self.dirpath())

        return open(self.__path, mode, encoding=encoding)
    
    def copyTo(self, target:str) -> any:
        shutil.copytree(self.path(), target, dirs_exist_ok=True)

    def mtime(self) -> float:
        return os.path.getmtime(self.__path)
    
    def ctime(self) -> float:
        return os.path.getctime(self.__path)

class Node(object):
    '''
    文档节点
    '''

    def __init__(self, path:str):
        self.__file:File = File(path)
        try:
            times = subprocess.run(["git", "log", "--reverse", "--format=%ai", path], encoding='utf-8', capture_output=True, text=True).stdout.splitlines()
            self.__ctime = datetime.strptime(times[0].strip(), "%Y-%m-%d %H:%M:%S %z")
            self.__mtime = datetime.strptime(times[-1].strip(), "%Y-%m-%d %H:%M:%S %z")
        except:
            self.__ctime = datetime.now()
            self.__mtime = datetime.now()
        self.__subs: list[Node] = []
        if self.__file.isdir():
            for sub in self.__file.listdir():
                self.__subs.append(Node(self.__file.join(sub).path()))

    def path(self) -> str:
        return self.__file.path()

    def filename(self) -> str:
        return self.__file.filename()

    def title(self) -> str:
        return file_title(self.__file.filename())
        
    def urlPath(self) -> str:
        return quote(self.title())
        
    def subs(self) -> list['Node']:
        return self.__subs
    
    def sub(self, index:int) -> 'Node':
        return self.__subs[index]

    def isdir(self) -> bool:
        return self.__file.isdir()
    
    def create_time(self) -> str:
        return self.__ctime.strftime("%Y-%m-%d %H:%M:%S")
    
    def update_time(self) -> str:
        return self.__mtime.strftime("%Y-%m-%d %H:%M:%S")
    
    def content(self) -> str:
        mark = mistune.create_markdown(renderer=MarkdownRenderer(PRIMERS_PREFIX, escape=True),
                                plugins=[
                                    'strikethrough', 
                                    'footnotes', 
                                    'table', 
                                    'url', 
                                    'task_lists', 
                                    'def_list', 
                                    'abbr', 
                                    'mark', 
                                    'insert', 
                                    'superscript', 
                                    'subscript', 
                                    'math'
                                ])
        with self.__file.open() as fp:
            return mark(fp.read())
        
    def brief(self) -> str:
        with self.__file.open() as fp:
            text = str(fp.read(150))
            return re.sub(r"[\s#>]+", "", text)


class Renderer(object):
    def __init__(self):
        self.__CURRENT_FILE = File(__file__)
        self.__CURRENT_DIR = File(self.__CURRENT_FILE.dirpath())
        self.__DOCUMENT = self.__CURRENT_DIR.join("templates", "document.html")
        self.__SITEMAP = self.__CURRENT_DIR.join("templates", "sitemap.txt")
        self.__STATIC_DIR = self.__CURRENT_DIR.join("..", "static")

    def clean(self):
        buidldir = self.__CURRENT_DIR.join("..", "build", PRIMERS_PREFIX)
        buidldir.remove()

    def copy_resource(self, res:str):
        target = self.__CURRENT_DIR.join("..", "build", PRIMERS_PREFIX, "resource")
        resource = File(res)
        resource.copyTo(target.path())

    def copy_static(self):
        target = self.__CURRENT_DIR.join("..", "build", PRIMERS_PREFIX)
        self.__STATIC_DIR.copyTo(target.path())

    def render_sitamap(self, root:Node):
        with self.__SITEMAP.open() as fp:
            renderer:Template = Template(fp.read())
            file = self.__CURRENT_DIR.join("..", "build", PRIMERS_PREFIX, "sitemap.txt")
            content = renderer.render(DOMAIN=PRIMERS_DOMAIN, PREFIX=PRIMERS_PREFIX, ROOT=root)

        with file.open("w") as fp:
            fp.write(content)

    def doc_path(self, category:Node, chapter:Node, doc:Node):
        if category.title() == "index":
            return "/index.html"
        elif category == doc:
            return f"/document/{doc.urlPath()}.html"
        elif chapter == doc:
            return f"/document/{category.urlPath()}/{doc.urlPath()}.html"
        else:
            return f"/document/{category.urlPath()}/{chapter.urlPath()}/{doc.urlPath()}.html"


    def render(self, root:Node, depth1:Node, depth2:Node, depth3:Node):

        title = ""
        title += f" - {depth1.title()}" if depth1.title() != "index" else ""
        title += f" - {depth2.title()}" if depth2.title() != "index" else ""
        title += f" - {depth3.title()}" if depth3.title() != "index" else ""
        
        with self.__DOCUMENT.open() as fp:
            renderer:Template = Template(fp.read())
            content = renderer.render(DOMAIN=PRIMERS_DOMAIN, 
                                      PREFIX=PRIMERS_PREFIX, 
                                      ROOT=root, 
                                      CATEGORY=depth1, 
                                      CHAPTER=depth2, 
                                      DOC=depth3, 
                                      TITLE=title, 
                                      CANONICAL=f"{PRIMERS_DOMAIN}{PRIMERS_PREFIX}{self.doc_path(depth1, depth2, depth3)}", 
                                      DESCRIPTION=depth3.brief(), 
                                      STYLE=html.HtmlFormatter(style='nord').get_style_defs('.highlight'))

        if depth3 == depth1:
            if depth1.title() == "index":
                file = self.__CURRENT_DIR.join("..", "build", PRIMERS_PREFIX, depth1.title() + '.html') # index 特殊处理，创建到根目录
            else:
                file = self.__CURRENT_DIR.join("..", "build", PRIMERS_PREFIX, "document", depth1.title() + '.html')
        elif depth3 == depth2:
            file = self.__CURRENT_DIR.join("..", "build", PRIMERS_PREFIX, "document", depth1.title(), depth2.title() + '.html')
        else:
            file = self.__CURRENT_DIR.join("..", "build", PRIMERS_PREFIX, "document", depth1.title(), depth2.title(), depth3.title() + '.html')

        with file.open("w") as fp:
            fp.write(content)


if __name__ == "__main__":
    CURRENT_FILE = File(__file__)
    CURRENT_DIR = File(CURRENT_FILE.dirpath())
    root:Node = Node(CURRENT_DIR.join('..', DOCUMENT_DIR).path())
    renderer:Renderer = Renderer()
    renderer.clean()
    renderer.copy_resource(CURRENT_DIR.join('..', RESOURCE_DIR).path())
    renderer.copy_static()
    renderer.render_sitamap(root)
    for category in root.subs():
        print(category.title())
        if category.isdir():
            for chapter in category.subs():
                print("\t", chapter.title())
                if chapter.isdir():
                    for doc in chapter.subs():
                        print("\t\t", doc.title())
                        renderer.render(root, category, chapter, doc)
                else:
                    renderer.render(root, category, chapter, chapter)
        else:
            renderer.render(root, category, category, category)