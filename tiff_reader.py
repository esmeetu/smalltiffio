import struct
import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

# Seek from beginning of file
SEEK_SET = 0
# Seek from current position.
SEEK_CUR = 1
# Seek from ending of file.
SEEK_END = 2

TIFF_ORDER_UNKNOWN = 0
TIFF_ORDER_BIGENDIAN = 1
TIFF_ORDER_LITTLEENDIAN = 2

TINYTIFFREADER_SAMPLEFORMAT_UINT = 1
TINYTIFFREADER_SAMPLEFORMAT_INT = 2
TINYTIFFREADER_SAMPLEFORMAT_FLOAT = 3
TINYTIFFREADER_SAMPLEFORMAT_UNDEFINED = 4

TIFF_FIELD_IMAGEWIDTH = 256
TIFF_FIELD_IMAGELENGTH = 257
TIFF_FIELD_BITSPERSAMPLE = 258
TIFF_FIELD_COMPRESSION = 259
TIFF_FIELD_PHOTOMETRICINTERPRETATION = 262
TIFF_FIELD_IMAGEDESCRIPTION = 270
TIFF_FIELD_STRIPOFFSETS = 273
TIFF_FIELD_SAMPLESPERPIXEL = 277
TIFF_FIELD_ROWSPERSTRIP = 278
TIFF_FIELD_STRIPBYTECOUNTS = 279
TIFF_FIELD_XRESOLUTION = 282
TIFF_FIELD_YRESOLUTION = 283
TIFF_FIELD_PLANARCONFIG = 284
TIFF_FIELD_RESOLUTIONUNIT = 296
TIFF_FIELD_SAMPLEFORMAT = 339

TIFF_TYPE_BYTE = 1
TIFF_TYPE_ASCII = 2
TIFF_TYPE_SHORT = 3
TIFF_TYPE_LONG = 4
TIFF_TYPE_RATIONAL = 5

TIFF_COMPRESSION_NONE = 1
TIFF_COMPRESSION_CCITT = 2
TIFF_COMPRESSION_PACKBITS = 32773

TIFF_PLANARCONFIG_CHUNKY = 1
TIFF_PLANARCONFIG_PLANAR = 2

TIFF_HEADER_SIZE = 510
TIFF_HEADER_MAX_ENTRIES = 16


class Tiff_Reader:

    def __init__(self):
        pass

    def open(self, filename):
        self.file = open(filename, 'rb')
        self.file_size = os.path.getsize(filename)

        self.currentFrame = self.StripFrame()
        self.byte_order = TIFF_ORDER_LITTLEENDIAN
        if (self.file and self.file_size > 0):
            sig = struct.unpack('B' * 4, self.file.read(4))
            if (sig == (73, 73, 42, 0)):
                self.byte_order = TIFF_ORDER_LITTLEENDIAN
            elif (sig == (77, 77, 0, 42)):
                self.byte_order = TIFF_ORDER_BIGENDIAN
            self.firstrecord_offset = self.read_int32()[0]
            self.nextifd_offset = self.firstrecord_offset
            self.read_next_frame()


    def close(self):
        self.file.close()

    def read_int8(self, n = 1):
        f = self.file
        if (self.byte_order == TIFF_ORDER_BIGENDIAN):
            return struct.unpack('>B' * n, f.read(1 * n))
        else:
            return struct.unpack('B' * n, f.read(1 * n))

    def read_int16(self, n = 2):
        f = self.file
        if (self.byte_order == TIFF_ORDER_BIGENDIAN):
            return struct.unpack('>H' * int(n/2), f.read(n))
        else:
            return struct.unpack('H' * int(n/2), f.read(n))
    

    def read_int32(self, n = 4):
        f = self.file
        if (self.byte_order == TIFF_ORDER_BIGENDIAN):
            return struct.unpack('>i' * int(n/4), f.read(n))
        else:
            return struct.unpack('i' * int(n/4), f.read(n))

    def read_ifd(self):
        ifd = self.IFD()
        ifd.tag = self.read_int16()[0]
        ifd.type = self.read_int16()[0]
        ifd.count = self.read_int32()[0]

        pos = self.file.tell()
        changepos = False

        if (ifd.type in (TIFF_TYPE_BYTE, TIFF_TYPE_ASCII)):
            if (ifd.count > 0):
                if (ifd.count <= 4):
                    for i in range(4):
                        value = self.read_int8()[0]
                        if (i < ifd.count):
                            ifd.pvalue.insert(i, value)
                else:
                    changepos = True
                    offset = self.read_int32()[0]
                    if (offset + ifd.count*1 <= self.file_size):
                        self.file.seek(offset)
                        for i in range(ifd.count):
                            ifd.pvalue.insert(i, self.read_int8()[0])
        elif (ifd.type == TIFF_TYPE_SHORT):
            if (ifd.count <= 2):
                for i in range(2):
                    value = self.read_int16()[0]
                    if (i < ifd.count):
                        ifd.pvalue.insert(i, value)
            else:
                changepos = True
                offset = self.read_int32()[0]
                if (offset + ifd.count*2 <= self.file_size):
                    self.file.seek(offset)
                    for i in range(ifd.count):
                        ifd.pvalue.insert(i, self.read_int16()[0])
        elif (ifd.type == TIFF_TYPE_LONG):
            if (ifd.count <= 1):
                ifd.pvalue[0] = self.read_int32()[0]
            else:
                changepos = True
                offset = self.read_int32()[0]
                if (offset + ifd.count*4 <= self.file_size):
                    self.file.seek(offset)
                    for i in range(ifd.count):
                        ifd.pvalue.insert(i, self.read_int32()[0])
        elif (ifd.type == TIFF_TYPE_RATIONAL):
            changepos = True
            offset = self.read_int32()[0]
            if (offset + ifd.count*4 <= self.file_size):
                self.file.seek(offset)
                for i in range(ifd.count):
                    ifd.pvalue.insert(i, self.read_int32()[0])
                    ifd.pvalue2.insert(i, self.read_int32()[0])
        else:
            ifd.value = self.read_int32()[0]

        if (ifd.pvalue):
            ifd.value = ifd.pvalue[0]
        if (ifd.pvalue2):
            ifd.value2 = ifd.pvalue[0]
        
        if (changepos):
            self.file.seek(pos)
            self.file.seek(4, SEEK_CUR) 
        return ifd

    class IFD:

        def __init__(self):
            self.tag = 0
            self.type = 0
            self.count = 0

            self.value = 0
            self.value2 = 0
            self.pvalue = []
            self.pvalue2 = []

    def has_next_frame(self):
        if (self.file):
            if (self.nextifd_offset > 0 and self.nextifd_offset < self.file_size):
                return True
        return False

    def read_next_frame(self):
        if not self.has_next_frame():
            return False

        self.currentFrame = self.StripFrame()
        if (self.nextifd_offset and self.nextifd_offset + 2 < self.file_size):
            self.file.seek(self.nextifd_offset)
            ifd_count = self.read_int16()[0]
            for i in range(ifd_count):
                ifd = self.read_ifd()
                
                tag = ifd.tag
                if (tag == TIFF_FIELD_IMAGEWIDTH):
                    self.currentFrame.width = ifd.value
                elif (tag == TIFF_FIELD_IMAGELENGTH):
                    self.currentFrame.height = ifd.value
                elif (tag == TIFF_FIELD_BITSPERSAMPLE):
                    self.currentFrame.bitspersample = ifd.pvalue
                elif (tag == TIFF_FIELD_COMPRESSION):
                    self.currentFrame.compression = ifd.value
                elif (tag == TIFF_FIELD_STRIPOFFSETS):
                    self.currentFrame.stripcount = ifd.count
                    self.currentFrame.stripoffsets = ifd.pvalue
                elif (tag == TIFF_FIELD_SAMPLESPERPIXEL):
                    self.currentFrame.samplesperpixel = ifd.value
                elif (tag == TIFF_FIELD_ROWSPERSTRIP):
                    self.currentFrame.rowsperstrip = ifd.value
                elif (tag == TIFF_FIELD_SAMPLEFORMAT):
                    self.currentFrame.sampleformat = ifd.value
                elif (tag == TIFF_FIELD_IMAGEDESCRIPTION):
                    if (ifd.count > 0):
                        for i in range(ifd.count):
                            self.currentFrame.description += chr(ifd.pvalue[i])
                elif (tag == TIFF_FIELD_STRIPBYTECOUNTS):
                    self.currentFrame.stripcount = ifd.count
                    self.currentFrame.stripbytecounts = ifd.pvalue
                elif (tag == TIFF_FIELD_PLANARCONFIG):
                    self.currentFrame.planarconfiguration = ifd.value
                else:
                    pass
            self.file.seek(self.nextifd_offset + 2 + 12 * ifd_count)
            self.nextifd_offset = self.read_int32()[0]
        else:
            print('no more images in tif file.')
            return False
        return True

    def get_sample_data(self, buf, sample):
        if (self.file):
            if (self.currentFrame.compression != TIFF_COMPRESSION_NONE):
                return False
            if (self.currentFrame.samplesperpixel > 1 and self.currentFrame.planarconfiguration != TIFF_PLANARCONFIG_PLANAR):
                return False
            if (self.currentFrame.width == 0 or self.currentFrame.height == 0):
                return False
            if (self.currentFrame.bitspersample[sample] not in (8, 16, 32)):
                return False
            
            pos = self.file.tell()
            tif = []
            if (self.currentFrame.stripcount > 0 and self.currentFrame.stripbytecounts and self.currentFrame.stripoffsets):
                if (self.currentFrame.bitspersample[sample] == 8):
                    for i in range(self.currentFrame.stripcount):
                        self.file.seek(self.currentFrame.stripoffsets[i])
                        buf = self.read_int8((self.currentFrame.stripbytecounts[i]))
                        offset = i * self.currentFrame.rowsperstrip * self.currentFrame.width
                elif (self.currentFrame.bitspersample[sample] == 16):
                    for i in range(self.currentFrame.stripcount):
                        self.file.seek(self.currentFrame.stripoffsets[i])
                        buf = self.read_int16((self.currentFrame.stripbytecounts[i]))
                        tif.append(buf)
                        offset = i * self.currentFrame.rowsperstrip * self.currentFrame.width
                        pixels = self.currentFrame.rowsperstrip * self.currentFrame.width
                        imagesize = self.currentFrame.width * self.currentFrame.height
                        if (offset + pixels > imagesize):
                            pixels = imagesize - offset
                elif (self.currentFrame.bitspersample[sample] == 32):
                    for i in range(self.currentFrame.stripcount):
                        self.file.seek(self.currentFrame.stripoffsets[i])
                        buf = self.read_int32((self.currentFrame.stripbytecounts[i]))
                        offset = i * self.currentFrame.rowsperstrip * self.currentFrame.width
            else:
                return False
            self.file.seek(pos)
            arr = np.asarray(tif)
            plt.imshow(arr, cmap='gray', vmin=0, vmax=255)
            plt.show()
            return True
        return False


    class StripFrame:

        def __init__(self):
            self.width = 0
            self.height = 0
            self.compression = TIFF_COMPRESSION_NONE 
            
            self.rowsperstrip = 0
            self.stripoffsets = []
            self.stripbytecounts = []
            self.stripcount = 0
            self.samplesperpixel = 1
            self.bitspersample = []
            self.planarconfiguration = TIFF_PLANARCONFIG_PLANAR
            self.sampleformat = TINYTIFFREADER_SAMPLEFORMAT_UINT 

            self.description = ''

    def count_frames(self):
        if (self.file):
            pos = self.file.tell()
            frames = 0
            next_offset = self.firstrecord_offset
            while (next_offset > 0):
                self.file.seek(next_offset)
                count = self.read_int16()[0]
                self.file.seek(count * 12, SEEK_CUR)
                next_offset = self.read_int32()[0]
                frames += 1
            
            self.file.seek(pos)
            return frames
    
if __name__ == "__main__":
    tiff_reader = Tiff_Reader()
    tiff_reader.open('')
    ok = True
    frame = 0

    frames = tiff_reader.count_frames()
    while (True):
        width = tiff_reader.currentFrame.width
        height = tiff_reader.currentFrame.height
        ok = (width == 6001) and (height == 6001)
        if not ok:
            print('ERROR in frame: size does not match, read width: %d, height: %d, expected width: %d, height: %d.', width, height, 6001, 6001)
        if ok:
            buf = ()
            ret = tiff_reader.get_sample_data(buf, 0)
            if not ret:
                print('ERROR: get_sample_data')
            # if (frame % 2 == 0):
            #     for i in range(width * height):
            frame += 1
        if not tiff_reader.read_next_frame():
            break
    
    print('frames: %d, frame: %d', frames, frame)

    tiff_reader.close()


