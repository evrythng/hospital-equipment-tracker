FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7



RUN pip install -U pip
RUN pip install certifi
RUN pip install chardet
RUN pip install click
RUN pip install fastapi
RUN pip install httpx
RUN pip install pydantic
RUN pip install requests
RUN pip install rfc3986
RUN pip install six
RUN pip install sniffio
RUN pip install ujson
RUN pip install uvicorn
RUN pip install uvloop
RUN pip install websockets
RUN pip install aiofiles
RUN pip install svglib
RUN pip install qrcode[pil]

COPY ./app /app
#ENTRYPOINT uvicorn main:app --host 0.0.0.0 --port 80 --timeout-keep-alive 540
