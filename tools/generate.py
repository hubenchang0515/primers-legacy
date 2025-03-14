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
from pygments.lexers import get_lexer_by_name
from pygments.formatters import html
from urllib.parse import quote
from jinja2 import Template

SELF_DOMAIN:str = "https://primers.planc.moe"
SELF_PREFIX:str = ""
SHIFT_DOMAIN:str = "https://shift.planc.moe"

class MarkdownRenderer(mistune.HTMLRenderer):
    '''
    Markdown 渲染器
    '''

    def __init__(self, prefix:str, escape=True, allow_harmful_protocols=None):
        super().__init__(escape, allow_harmful_protocols)
        self.__prefix = prefix

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
            return f"<div class='{classList}'>{content}</div>"
        else:
            return f"<p class='view-p'>{text}</p>"
    
    def link(self, text, url, title=None):
        if title:
            return f"<a class='view-text-primary' title='{title}' href='{url}' target='_blank'>{text}</a>"
        else:
            return f"<a class='view-text-primary' href='{url}' target='_blank'>{text}</a>"
    
    def block_quote(self, text):
        return f"<div><blockquote>{text}</blockquote></div>"

    def list(self, text, ordered, **attrs):
        if ordered:
            return f"<div><ol>{text}</ol></div>"
        else:
            return f"<div><ul>{text}</ul></div>"
        
    def table(self, text):
        return f"<table class='view-width-100'>{text}</table>"

    def image(self, text, url, title=None):
        if url.startswith("/") and not url.startswith(self.__prefix):
            wrapUrl = f"/{self.__prefix}/{url[1:]}"
            return f"<img class='view-dark-filter' src='{wrapUrl}' alt='{text}' title={title}>"

        return f"<img class='view-dark-filter' src='{url}' alt='{text}' title={title}>"
    
    def codespan(self, text):
        text = text.replace("&amp;", "&")
        return f"<code class='view-text-secondary view-border-1 view-border-secondary'>{text}</code>"
    
    def block_code(self, code, info=None):
        if not info:
            return f'<pre><code>{mistune.escape(code)}</code></pre>\n'
        
        infos = info.split(" ")
        
        if len(infos) > 1 and infos[1] == 'shift':
            desc:str = mistune.escape(code).replace("\n", r"\n").replace("'", '"')
            b64code:str = base64.b64encode(quote(code).encode('utf-8')).decode('utf-8')

            if len(infos) > 2:
                b64input:str = base64.b64encode(quote(infos[2]).encode('utf-8')).decode('utf-8')
                return f" <iframe width='100%' height='600' loading='lazy' title='{desc}' aria-describedby='{desc}' src='{SHIFT_DOMAIN}/index.html?lang={infos[0]}&input={b64input}&code={b64code}'></iframe>"
            else:
                return f" <iframe width='100%' height='600' loading='lazy' title='{desc}' aria-describedby='{desc}' src='{SHIFT_DOMAIN}/index.html?lang={infos[0]}&code={b64code}'></iframe>"
        else:
            lexer = get_lexer_by_name(infos[0], stripall=True)
            formatter = html.HtmlFormatter(style='nord')
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

    def title(self) -> str:
        items:list[str] = self.__file.filename().split(".")
        if len(items) == 0:
            return "未命名"
        elif len(items) == 1 or not items[0].isdigit():
            return items[0]
        else:
            return items[1]
        
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
        mark = mistune.create_markdown(renderer=MarkdownRenderer("", escape=False),
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
        self.__RESOURCE_DIR = self.__CURRENT_DIR.join("..", "resource")
        self.__STATIC_DIR = self.__CURRENT_DIR.join("..", "static")

    def clean(self):
        buidldir = self.__CURRENT_DIR.join("..", "build", "Primers")
        buidldir.remove()

    def copy_resource(self):
        targer = self.__CURRENT_DIR.join("..", "build", "Primers", "resource")
        self.__RESOURCE_DIR.copyTo(targer.path())

    def copy_static(self):
        targer = self.__CURRENT_DIR.join("..", "build", "Primers")
        self.__STATIC_DIR.copyTo(targer.path())

    def render_sitamap(self, root:Node):
        with self.__SITEMAP.open() as fp:
            renderer:Template = Template(fp.read())
            file = self.__CURRENT_DIR.join("..", "build", "Primers", "sitemap.txt")
            content = renderer.render(DOMAIN=SELF_DOMAIN, PREFIX=SELF_PREFIX, ROOT=root)

        with file.open("w") as fp:
            fp.write(content)

    def render(self, root:Node, depth1:Node, depth2:Node, depth3:Node):

        title = ""
        title += f" - {depth1.title()}" if depth1.title() != "index" else ""
        title += f" - {depth2.title()}" if depth2.title() != "index" else ""
        title += f" - {depth3.title()}" if depth3.title() != "index" else ""
        
        with self.__DOCUMENT.open() as fp:
            renderer:Template = Template(fp.read())
            content = renderer.render(PREFIX=SELF_PREFIX, ROOT=root, CATEGORY=depth1, CHAPTER=depth2, DOC=depth3, TITLE=title, DESCRIPTION=depth3.brief(), STYLE=html.HtmlFormatter(style='nord').get_style_defs('.highlight'))

        if depth3 == depth1:
            file = self.__CURRENT_DIR.join("..", "build", "Primers", depth1.title() + '.html')
        elif depth3 == depth2:
            file = self.__CURRENT_DIR.join("..", "build", "Primers", depth1.title(), depth2.title() + '.html')
        else:
            file = self.__CURRENT_DIR.join("..", "build", "Primers", depth1.title(), depth2.title(), depth3.title() + '.html')

        with file.open("w") as fp:
            fp.write(content)


if __name__ == "__main__":
    root:Node = Node("./document")
    renderer:Renderer = Renderer()
    renderer.clean()
    renderer.copy_resource()
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