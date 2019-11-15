import os
import shutil

from bitstring import ConstBitStream

from pybzparse import Parser
from pybzparse.utils import get_trak_sample, find_boxes

from pyheifconcat.index_metadata import index_metadata, parse_args


PWD = "tests_tmp"

if PWD and not os.path.exists(PWD):
    os.makedirs(PWD)

os.chdir(PWD)


def test_index_metadata():
    container_filename = "concat.bzna"
    shutil.copyfile("../test_datasets/mini_dataset_to_concat/concat.bzna",
                    container_filename, follow_symlinks=True)

    try:
        args = parse_args([container_filename])

        index_metadata(args)

        assert not os.path.exists(container_filename + ".moov")

        bstr = ConstBitStream(filename=container_filename)
        boxes = list(Parser.parse(bstr))

        # mdat should be using the box extended size field to prevent having to
        # shift data if it is bigger than the limit of the regular box size field
        mdat = next(find_boxes(boxes, b"mdat"))
        assert mdat.header.box_ext_size is not None

        moov = next(find_boxes(boxes, b"moov"))
        moov.load(bstr)

        samples = [get_trak_sample(bstr, moov.boxes, b"bzna_input\0", i) for i in range(9)]
        targets = [get_trak_sample(bstr, moov.boxes, b"bzna_target\0", i) for i in range(9)]
        filenames = [get_trak_sample(bstr, moov.boxes, b"bzna_fname\0", i) for i in range(9)]

        for sample, target, filename in zip(samples, targets, filenames):
            sample_bstr = ConstBitStream(bytes=sample)
            sample_moov = next(find_boxes(Parser.parse(sample_bstr), b"moov"))
            sample_moov.load(sample_bstr)
            assert target == get_trak_sample(sample_bstr, sample_moov.boxes, b"bzna_target\0", 0)
            assert filename == get_trak_sample(sample_bstr, sample_moov.boxes, b"bzna_fname\0", 0)

    finally:
        shutil.rmtree(".", ignore_errors=True)


def test_retry_index_metadata():
    container_filename = "concat_indexed.bzna"
    shutil.copyfile("../test_datasets/mini_dataset_to_concat/concat_indexed.bzna",
                    container_filename, follow_symlinks=True)

    try:
        args = parse_args([container_filename])

        index_metadata(args)

        assert not os.path.exists(container_filename + ".moov")

        bstr = ConstBitStream(filename=container_filename)
        boxes = list(Parser.parse(bstr))

        # mdat should be using the box extended size field to prevent having to
        # shift data if it is bigger than the limit of the regular box size field
        mdat = next(find_boxes(boxes, b"mdat"))
        assert mdat.header.box_ext_size is not None

        moov = next(find_boxes(boxes, b"moov"))
        moov.load(bstr)

        samples = [get_trak_sample(bstr, moov.boxes, b"bzna_input\0", i) for i in range(9)]
        targets = [get_trak_sample(bstr, moov.boxes, b"bzna_target\0", i) for i in range(9)]
        filenames = [get_trak_sample(bstr, moov.boxes, b"bzna_fname\0", i) for i in range(9)]

        for sample, target, filename in zip(samples, targets, filenames):
            sample_bstr = ConstBitStream(bytes=sample)
            sample_moov = next(find_boxes(Parser.parse(sample_bstr), b"moov"))
            sample_moov.load(sample_bstr)
            assert target == get_trak_sample(sample_bstr, sample_moov.boxes, b"bzna_target\0", 0)
            assert filename == get_trak_sample(sample_bstr, sample_moov.boxes, b"bzna_fname\0", 0)

    finally:
        shutil.rmtree(".", ignore_errors=True)


def test_parse_args():
    raw_arguments = ["container_name.bzna"]

    try:
        with open(raw_arguments[0], "wb"):
            pass
        
        args = parse_args(raw_arguments)
        assert args.container.name == "container_name.bzna"

    finally:
        shutil.rmtree(".", ignore_errors=True)
