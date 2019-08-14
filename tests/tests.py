import glob, os, shutil, subprocess

from pyheifconcat import concat, transcode, parse_args

TESTS_WORKING_DIR = os.path.abspath('.')

os.environ["PATH"] = ':'.join([os.environ["PATH"],
                               os.path.join(TESTS_WORKING_DIR, "mocks")])

PWD = "tests_tmp"

if PWD and not os.path.exists(PWD):
    os.makedirs(PWD)

os.chdir(PWD)


def test_concat():
    src = "input/dir/"
    dest = "output/dir/concat.bza"
    src_dir = os.path.dirname(src)
    dest_dir = os.path.dirname(dest)
    queued_dir = os.path.join(src_dir, "queue")
    completed_list_filepath = os.path.join(src_dir, "completed_list")

    to_concat_filepaths = []
    for i in range(10):
        to_concat_filepaths.append(os.path.join(queued_dir,
                                                "file_{}_5mb.img".format(i)))

    args = parse_args(["concat", src, dest])

    try:
        if queued_dir and not os.path.exists(queued_dir):
            os.makedirs(queued_dir)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        processes = []
        for i, to_concat_filepath in enumerate(to_concat_filepaths):
            processes.append(
                subprocess.Popen(["dd", "if=/dev/urandom",
                                  "of={}".format(to_concat_filepath),
                                  "bs=1000", "count=5000"]))

        concat_bytes = []
        for i, process in enumerate(processes):
            process.wait()
            with open(to_concat_filepaths[i], "rb") as file:
                concat_bytes.append(file.read())
                assert len(concat_bytes[i]) == 5000 * 1000

        concat_bytes = b''.join(concat_bytes)
        assert len(concat_bytes) == 5000 * 1000 * 10

        concat(args)

        with open(args.dest, "rb") as file:
            assert file.read() == concat_bytes

        with open(completed_list_filepath, "r") \
             as completed_list:
            assert list(filter(None, completed_list.read().split('\n'))) == \
                   to_concat_filepaths

    finally:
        shutil.rmtree(".", ignore_errors=True)


def test_concat_no_queue():
    src = "input/dir/"
    dest = "output/dir/concat.bza"
    src_dir = os.path.dirname(src)
    completed_list_filepath = os.path.join(src_dir, "completed_list")

    to_concat_filepaths = []

    args = parse_args(["concat", src, dest])

    try:
        concat_bytes = b''
        concat(args)

        with open(args.dest, "rb") as file:
            assert file.read() == concat_bytes

        with open(completed_list_filepath, "r") \
             as completed_list:
            assert list(filter(None, completed_list.read().split('\n'))) == \
                   to_concat_filepaths

    finally:
        shutil.rmtree(".", ignore_errors=True)


def _test_trancode(tmp_filepaths, nb_files_to_skip, tmp_dir, dest_dir, args):
    uploaded_dir = os.path.join(dest_dir, "upload")
    queued_dir = os.path.join(dest_dir, "queue")
    completed_list_filepath = os.path.join(dest_dir, "completed_list")

    if tmp_dir and not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    if uploaded_dir and not os.path.exists(uploaded_dir):
        os.makedirs(uploaded_dir)
    if queued_dir and not os.path.exists(queued_dir):
        os.makedirs(queued_dir)

    processes = []
    for i, tmp_filepath in enumerate(tmp_filepaths):
        processes.append(
            subprocess.Popen(["dd", "if=/dev/urandom",
                              "of={}".format(tmp_filepath),
                              "bs=1000", "count=5000"]))

    files_bytes = []
    for i, process in enumerate(processes):
        process.wait()
        with open(tmp_filepaths[i], "rb") as file:
            files_bytes.append(file.read())
            assert len(files_bytes[i]) == 5000 * 1000

    with open(completed_list_filepath, "w") as completed_list_file:
        for tmp_filepath in tmp_filepaths[:nb_files_to_skip]:
            tmp_filename = os.path.basename(tmp_filepath)
            completed_list_file.write(os.path.join(queued_dir, tmp_filename))
            completed_list_file.write('\n')

    transcode(args)

    assert len(glob.glob(os.path.join(tmp_dir, '*'))) == nb_files_to_skip
    assert len(glob.glob(os.path.join(uploaded_dir, '*'))) == 0

    queued_list = glob.glob(os.path.join(queued_dir, '*'))
    queued_list.sort()
    assert len(queued_list) == \
           len(tmp_filepaths) - nb_files_to_skip

    for i, filepath in enumerate(queued_list):
        with open(filepath, "rb") as file:
            file_bytes = file.read()
            assert file_bytes == files_bytes[i + nb_files_to_skip]


def test_trancode():
    dest = "output/dir/"
    dest_dir = os.path.dirname(dest)
    tmp_dir = "tmp_test"

    tmp_filepaths = []
    for i in range(10):
        tmp_filepaths.append(os.path.join(tmp_dir, "file_{}_5mb.img".format(i)))

    args = parse_args(["transcode", ','.join(tmp_filepaths), dest])

    try:
        _test_trancode(tmp_filepaths, 0, tmp_dir, dest_dir, args)

    finally:
        shutil.rmtree(".", ignore_errors=True)


def test_trancode_completed_3():
    dest = "output/dir/"
    dest_dir = os.path.dirname(dest)
    tmp_dir = "tmp_test"

    tmp_filepaths = []
    for i in range(10):
        tmp_filepaths.append(os.path.join(tmp_dir, "file_{}_5mb.img".format(i)))

    args = parse_args(["transcode", ','.join(tmp_filepaths), dest])

    try:
        _test_trancode(tmp_filepaths, 3, tmp_dir, dest_dir, args)

    finally:
        shutil.rmtree(".", ignore_errors=True)


def test_action_redirection():
    raw_concat_arguments = ["concat", "src_concat", "dest_concat"]

    raw_transcode_arguments = ["transcode",
                               "src_transcode",
                               "dest_transcode",
                               "--ssh-remote", "remote_transcode",
                               "--tmp", "tmp_transcode"]

    raw_extract_hdf5_arguments = ["extract_hdf5",
                                  "src_extract_hdf5",
                                  "dest_extract_hdf5",
                                  "--start", "10",
                                  "--number", "15",
                                  "--transcode",
                                  "--ssh-remote", "remote_extract_hdf5",
                                  "--tmp", "tmp_extract_hdf5"]

    args = parse_args(raw_concat_arguments)

    assert args.action == "concat"
    assert args.src == "src_concat"
    assert args.dest == "dest_concat"

    args = parse_args(raw_transcode_arguments)

    assert args.action == "transcode"
    assert args.src == "src_transcode"
    assert args.dest == "dest_transcode"
    assert args.ssh_remote == "remote_transcode"
    assert args.tmp == "tmp_transcode"

    args = parse_args(raw_extract_hdf5_arguments)

    assert args.action == "extract_hdf5"
    assert args.src == "src_extract_hdf5"
    assert args.dest == "dest_extract_hdf5"
    assert args.start == 10
    assert args.number == 15
    assert args.ssh_remote == "remote_extract_hdf5"
    assert args.tmp == "tmp_extract_hdf5"
