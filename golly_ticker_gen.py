
import re

class rle_loader(object):

    def __init__(self):
        pass

    def load_file(self, fn):
        with open(fn, 'rU') as fd:
            self.load(fd)

    def load(self, fd):
        self.state = 'sta_ready'
        line = fd.readline()
        while(line):
            self.parse_line(line)
            line = fd.readline()
        assert self.state == 'sta_done'
        self.parse_content()
        self.lm.strip()

    def parse_line(self, line):
        self.state = getattr(self, self.state)(line)

    def sta_ready(self, line):
        r = re.match('\s*#', line)
        if r:
            return 'sta_ready'
        r = re.match('\s*x\s*=\s*(\d*).*[ ,]y\s*=\s*(\d*)', line)
        if r:
            self.width = int(r.groups()[0])
            self.height = int(r.groups()[1])
            self.content = ''
            return 'sta_content'
        return 'sta_halt'

    def sta_content(self, line):
        self.content += line.strip()
        r = re.match('.*!', line)
        if r:
            self.content = re.match('(.*[^\$])\$*!', self.content).groups()[0]
            return 'sta_done'
        return 'sta_content'

    def sta_done(self, line):
        return 'sta_done'

    def parse_content(self):
        self.lm = l_matrix()
        st = 'sta_c_ready'
        arg = ([0, 0], )
        i = 0
        while i < len(self.content):
            c = self.content[i]
            st, go, arg = getattr(self, st)(c, *arg)
            if(go):
                i += 1
        assert st == 'sta_c_ready'
        
    def sta_c_ready(self, c, pos):
        if c.isdigit():
            return 'sta_c_digit', True, (c, pos)
        else:
            return 'sta_c_symb', False, (1, pos)
        
    def sta_c_digit(self, c, cnt, pos):
        if c.isdigit():
            cnt += c
            return 'sta_c_digit', True, (cnt, pos)
        else:
            return 'sta_c_symb', False, (int(cnt), pos)

    def sta_c_symb(self, c, cnt, pos):
        if c == 'o':
            self.lm.setp(pos, cnt, 1)
            pos[0] += cnt
            assert pos[0] <= self.width
            return 'sta_c_ready', True, (pos, )
        elif c == 'b':
            #self.lm.setp(pos, cnt, 0)
            pos[0] += cnt
            assert pos[0] <= self.width
            return 'sta_c_ready', True, (pos, )
        elif c == '$':
            pos[0] = 0
            pos[1] += cnt
            assert pos[1] <= self.height
            return 'sta_c_ready', True, (pos, )
        else:
            return 'sta_c_halt', False, (None, )

    def import_lm(self, lm):
        self.lm = lm

    def save_file(self, fn):
        with open(fn, 'w') as fd:
            self.save_rle(fd)

    def save_rle(self, fd):
        self.make_content()
        fd.write('x = {:d}, y = {:d}, rule = B3/S23\n'.format(self.width, self.height))
        cw = 40
        s = (self.content + '!').split('$')
        l = 0
        sh = s.pop(0)
        fd.write(sh)
        while s:
            fd.write('$')
            l += len(sh) + 1
            if(l > 40):
                fd.write('\n')
                l = 0
            sh = s.pop(0)
            fd.write(sh)

    def make_content(self):
        self.content = ''
        self.width = self.lm.width #- self.lm.x + 1
        self.height = self.lm.height #- self.lm.y + 1
        st = 'sta_m_ready'
        cnt = 0
        for y in range(0, self.height):
            for x in range(0, self.width):
                try:
                    val = self.lm.mx[y][x]
                except KeyError:
                    val = 0
                st, cnt = getattr(self, st)(val, cnt)
            st, cnt = getattr(self, st)('$', cnt)
        assert st == 'sta_m_newline'

    def sta_m_ready(self, v, cnt):
        if v == '$':
            return 'sta_m_newline', 0
        elif v == 0:
            return 'sta_m_blank', 1
        else:
            return 'sta_m_point', 1
    def sta_m_newline(self, v, cnt):
        if v == '$':
            return 'sta_m_newline', cnt
        elif v == 0:
            return 'sta_m_newline', cnt + 1
        else:
            if cnt >= self.width:
                self.content += str(cnt/self.width+1) + '$'
                cnt = cnt % self.width
            else:
                self.content += '$'
            if cnt > 1:
                self.content += str(cnt) + 'b'
            elif cnt == 1:
                self.content += 'b'
            return 'sta_m_point', 1
    def sta_m_blank(self, v, cnt):
        if v == '$':
            return 'sta_m_newline', 0
        elif v == 0:
            return 'sta_m_blank', cnt + 1
        else:
            if cnt > 1:
                self.content += str(cnt) + 'b'
            else:
                self.content += 'b'
            return 'sta_m_point', 1
    def sta_m_point(self, v, cnt):
        if v == '$':
            if cnt > 1:
                self.content += str(cnt) + 'o'
            else:
                self.content += 'o'
            return 'sta_m_newline', 0
        elif v == 0:
            if cnt > 1:
                self.content += str(cnt) + 'o'
            else:
                self.content += 'o'
            return 'sta_m_blank', 1
        else:
            return 'sta_m_point', cnt + 1

class l_matrix(object):

    def __init__(self):
        self.x = 0
        self.y = 0
        self.mx = {}

    def setp(self, pos, cnt, val):
        y = pos[1] - self.y
        rx = pos[0] - self.x
        if not(y in self.mx):
            self.mx[y] = {}
        for x in range(rx, rx + cnt):
            self.mx[y][x] = val

    def strip(self):
        top = bot = left = right = None
        for y in self.mx:
            row = self.mx[y]
            for x in row:
                if row[x] != 0:
                    if top == None or top > y:
                        top = y
                    if bot == None or bot < y:
                        bot = y
                    if left == None or left > x:
                        left = x
                    if right == None or right < x:
                        right = x
        self.x = left
        self.y = top
        self.width = right - left
        self.height = bot - top
        if self.x > 0 or self.y > 0:
            r = {}
            for y in self.mx:
                row = self.mx[y]
                r[y - self.y] = {}
                for x in row:
                    r[y - self.y][x - self.x] = row[x]
            self.mx = r

    def add(self, lm, pos):
        rslt = type(self)()
        lx = lm.x + pos[0]
        ly = lm.y + pos[1]
        rslt.x = min(self.x, lx)
        rslt.y = min(self.y, ly)
        rslt.width = max(self.width + self.x, lm.width + lx) - rslt.x
        rslt.height = max(self.height + self.y, lm.height + ly) - rslt.y
        for y in self.mx:
            row = self.mx[y]
            rslt.mx[y + self.y - rslt.y] = {}
            for x in row:
                rslt.mx[y + self.y - rslt.y][x + self.x - rslt.x] = row[x]
        for y in lm.mx:
            row = lm.mx[y]
            _y = y + ly - rslt.y
            if not (_y in rslt.mx):
                rslt.mx[_y] = {}
            for x in row:
                _x = x + lx - rslt.x
                if _x in rslt.mx[_y]:
                    rslt.mx[_y][_x] += row[x]
                else:
                    rslt.mx[_y][_x] = row[x]
        return rslt

    def sub(self, pos, size):
        rslt = type(self)()
        rslt.x = self.x + pos[0]
        rslt.y = self.y + pos[1]
        rslt.width = size[0]
        rslt.height = size[1]
        for y in range(0, size[1]):
            for x in range(0, size[0]):
                try:
                    v = self.mx[y + pos[1]][x + pos[0]]
                except KeyError:
                    pass
                else:
                    if not (y in rslt.mx):
                        rslt.mx[y] = {}
                    rslt.mx[y][x] = v
        return rslt

    def trans(self, trans = lambda a,b:(a,b)):
        rslt = type(self)()
        rslt.x = self.x
        rslt.y = self.y
        rslt.width, rslt.height = trans(self.width, self.height)
        if rslt.width < 0: rslt.width = - rslt.width - 1
        if rslt.height < 0: rslt.height = - rslt.height - 1
        def tr(x, y):
            nx, ny = trans(x, y)
            if nx < 0: nx = rslt.width + nx
            if ny < 0: ny = rslt.height + ny
            return nx, ny
        for y in self.mx:
            row = self.mx[y]
            for x in row:
                nx, ny = tr(x, y)
                if not (ny in rslt.mx):
                    rslt.mx[ny] = {}
                rslt.mx[ny][nx] = row[x]
        return rslt

    def cut(self, pos, size):
        for y in range(pos[1], pos[1] + size[1]):
            for x in range(pos[0], pos[0] + size[0]):
                if y in self.mx:
                    if x in self.mx[y]:
                        del self.mx[y][x]
                        if not self.mx[y]:
                            del self.mx[y]

class golly_ticker_patt(object):

    def __init__(self, pattfile):
        self.src = rle_loader()
        with open(pattfile, 'rU') as fd:
            self.src.load(fd)
        self.hndl_lm = self.src.lm.trans()
        self.g_size = 9
        self.eater_lm = self.hndl_lm.sub([0, 0], [4, 4])
        self.eater_lm.x = self.eater_lm.y = 0
        self.hndl_lm.cut([0, 0], [4, 4])
        self.gliders_lm = self.hndl_lm.sub(*self.gliders_pos(0))
        self.gliders_lm.x = self.gliders_lm.y = 0
        for i in range(0, self.g_size):
            self.hndl_lm.cut(*self.gliders_pos(i))
        self.head_lm = self.hndl_lm.sub(*self.head_pos())
        self.head_lm.x = self.head_lm.y = 0
        self.tail_lm = self.hndl_lm.sub(*self.tail_pos())
        self.tail_lm.x = self.tail_lm.y = 0

    def make_gtpatt(self, size):
        self.g_size = size
        self.head_lm.x, self.head_lm.y = self.head_pos()[0]
        self.tail_lm.x, self.tail_lm.y = self.tail_pos()[0]
        self.patt_lm = self.head_lm.add(self.tail_lm, [0, 0])
        for i in range(0, self.g_size):
            self.patt_lm = self.patt_lm.add(self.gliders_lm, self.gliders_pos(i)[0])

    def gliders_pos(self, idx):
        x = 28 + idx * 23
        y = 20 + (self.g_size - 1 - idx) * 23
        return [x, y], [35, 32]

    def head_pos(self):
        y = self.g_size * 23 - 3
        return [0, y], [90, 86]

    def tail_pos(self):
        x = self.g_size * 23 + 18
        return [x, 0], [41, 42]

    def glider_vol(self):
        return self.g_size * 4 + 5

    def size(self):
        return [self.g_size * 23 + 59, self.g_size * 23 + 83]

    def glider_pos(self, idx):
        stp = [self.g_size * 2, 2, self.g_size * 2, 3]
        tn = [sum(stp[:i]) for i in range(1, len(stp)+1)]
        if idx < tn[0]:
            pidx = idx
            nidx = tn[0] - idx
            bx = 28
            by = 8
            x = int(pidx/2) * 23 + bx
            y = int(nidx/2) * 23 + by
            if pidx % 2:
                x += 12
                y += 12
        elif idx < tn[1]:
            pidx = idx - tn[0]
            bx = self.g_size * 23 + 29
            by = 14
            x = int(pidx/2) * 23 + bx
            y = int(pidx/2) * 23 + by 
            if pidx % 2:
                x += 12
                y += 11
        elif idx < tn[2]:
            pidx = idx - tn[1]
            nidx = tn[2] - idx
            bx = 49
            by = 26
            x = int(pidx/2) * 23 + bx
            y = int(nidx/2) * 23 + by
            if pidx % 2:
                x += 11
                y += 11
        elif idx < tn[3]:
            pidx = idx - tn[2]
            by = self.g_size * 23 + 23
            if pidx == 0:
                x = 37
                y = by + 14
            elif pidx == 1:
                x = 27
                y = by + 11
            elif pidx == 2:
                x = 15
                y = by
        return [x, y]

class golly_ticker(object):

    def __init__(self, pattfile):
        self.gt_patt = golly_ticker_patt(pattfile)
        self.distx = 18
        self.distp = 5

    def calc_parm(self, width, height, length):
        self.g_size = int((width - 6) / 4) + 1
        self.width = self.g_size * 4 + 5
        self.length = (int((length - 1) / 4) + 1) * 4
        self.height = height
        self.p_cnt_p = int((height - 1) / 2) + 1
        self.p_cnt_n = int(height/2)

    def make_gtpatt(self):
        self.gt_patt.make_gtpatt(self.g_size)
        self.patt_lm_p = self.gt_patt.patt_lm.trans()
        self.patt_lm_n = self.gt_patt.patt_lm.trans(lambda a,b:(a,-b-1))
        self.eater_lm_p = self.gt_patt.eater_lm.trans()
        self.eater_lm_n = self.gt_patt.eater_lm.trans(lambda a,b:(a,-b-1))

    def calc_patt_pos(self, i, p = True):
        if p:
            return [self.distp * 23 * i, self.distx * i]
        else:
            return [self.distp * 23 * (self.p_cnt_n - 1 - i),
                    self.gt_patt.size()[1] - 13 + self.distx * (i + self.p_cnt_p)]

    def calc_glider_pos(self, g, i):
        gpos = self.gt_patt.glider_pos(g)
        idx = i
        if i >= self.p_cnt_p:
            gsize = self.gt_patt.size()
            gpos[1] = gsize[1] - gpos[1] - 3
            idx = i - self.p_cnt_p
        ppos = self.calc_patt_pos(idx, i < self.p_cnt_p)
        return [gpos[0] + ppos[0], gpos[1] + ppos[1]]

    def calc_eater_pos(self, i):
        y = self.gt_patt.size()[1] - 5 + i * self.distx
        ph = i%2
        if i >= self.p_cnt_p:
            ph = (self.height - i) % 2
        else:
            ph = i % 2
        if ph: y -= 7
        return ph, [1 - self.length, y]

    def make_gt(self, width, height, length):
        self.calc_parm(width, height, length)
        self.make_gtpatt()
        self.patt_lm_p.x = self.patt_lm_p.y = 0
        self.gt_lm = self.patt_lm_p.trans()
        for i in range(1, self.p_cnt_p):
            self.gt_lm = self.gt_lm.add(
                self.patt_lm_p, self.calc_patt_pos(i, True))
        for i in range(0, self.p_cnt_n):
            self.gt_lm = self.gt_lm.add(
                self.patt_lm_n, self.calc_patt_pos(i, False))
        for i in range(0, self.height):
            et, etp = self.calc_eater_pos(i)
            if et:
                self.gt_lm = self.gt_lm.add(
                    self.eater_lm_n, etp)
            else:
                self.gt_lm = self.gt_lm.add(
                    self.eater_lm_p, etp)

    def clear_glider(self, x, y):
        px, py = self.calc_glider_pos(x, y)
        self.gt_lm.cut([px - self.gt_lm.x, py - self.gt_lm.y], [3, 3])

if __name__ == '__main__':
    gt = golly_ticker('template.rle')
    rslt = rle_loader()
    gt.make_gt(27, 9, 200)
    for i in range(0, 27):
        for j in range(0, 9):
            gt.clear_glider(i, j)
    rslt.import_lm(gt.gt_lm)
    rslt.save_file('result.rle')
    
