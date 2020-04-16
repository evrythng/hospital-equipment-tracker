import qrcode
from qrcode.image import svg
import io
from PIL import ImageFont


class UrlQRCode:

    def __init__(self, url, box_size=10, border=1):
        self.__error_correction = qrcode.constants.ERROR_CORRECT_H
        self.__box_size = box_size
        self.__border = border
        self.__data = url
        self.__image = None
        self.image()

    def image(self):
        if self.__image:
            return self.__image
        else:
            qr = qrcode.QRCode(
                error_correction=self.__error_correction,
                box_size=self.__box_size,
                border=self.__border,
                image_factory=svg.SvgImage
            )

            qr.add_data(self.__data)
            qr.make(fit=True)

            self.__image = qr.make_image(fill_color="black", back_color="white")

            return self.__image

    @property
    def height(self):
        return self.image().box_size * self.image().width
    @property
    def width(self):
        return self.image().box_size * self.image().width

    def __str__(self):
        b_io = io.BytesIO()
        self.image().save(b_io)
        b_io.seek(0)
        return b''.join(b_io.readlines()).decode()


class TextLabel:

    def __init__(self, data: str):
        self.__data = data
        font = ImageFont.truetype('times.ttf', 12)
        self.__width = font.getsize(data)
        self.__height = 12

    @property
    def height(self):
        return self.__height

    @property
    def width(self):
        return self.__width

    def __str__(self):
        return self.__data


class FillLine:

    def __init__(self):
        self.mem = {}

    def __new_tag__(self, int  box_size, dict tag):
        self.mem[(box_size, tag['url'])] = self.mem.get((box_size, tag['url']),
                                                        UrlQRCode(box_size=box_size, url=tag['url']))
        return self.mem[(box_size, tag['url'])]

    def __call__(self, int box_size, int text_width, list tags):
        cdef int used_space = 0
        cdef int i = 0
        for i, u in enumerate(tags):
            q = self.__new_tag__(box_size=box_size, tag=u)
            if used_space + q.width <= text_width:
                used_space += q.width
            else:
                break
        return i + 1, box_size


cdef optimal_label_size(int min_box_size, int max_box_size, int text_width, tags, fill_line):
    cdef int m, c_columns, m_columns
    m = (min_box_size + max_box_size) // 2
    if min_box_size <= m <= max_box_size:
        current_size = fill_line(m, text_width, tags)
        min_size = optimal_label_size(min_box_size, m - 1, text_width, tags, fill_line)
        c_columns = current_size[0]
        m_columns = min_size[0]
        if c_columns > m_columns:
            return max(current_size, optimal_label_size(m + 1, max_box_size, text_width, tags, fill_line))
        else:
            return min_size
        # return max(fill_line(m, text_width, urls),
        #            optimal_label_size(min_box_size, m - 1, text_width, urls),
        #            optimal_label_size(m + 1, max_box_size, text_width, urls))
    else:
        return 0, 0

def next_row(int min_box_size, int max_box_size, int text_width, tags):
    cdef int rows, box_size
    fill_line = FillLine()
    while tags:
        rows, box_size = optimal_label_size(min_box_size, max_box_size, text_width, tags, fill_line)
        max_box_size = min(box_size, max_box_size)
        yield [dict(qr=fill_line.mem[(box_size, tag['url'])], label=tag['label']) for tag in tags[:rows]]
        tags = tags[rows:]
