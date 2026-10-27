from checks.performance import check_performance, parse_ps, parse_vm_stat
from checks.ports import Listener, check_ports, parse_lsof
from conftest import FIXTURES, fake_run

LSOF_SAMPLE = (FIXTURES / "lsof_listen.txt").read_text()
VM_OK = (FIXTURES / "vm_stat.txt").read_text()
VM_LOW = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                                     1000.
Pages active:                                 900000.
Pages inactive:                                 2000.
Pages speculative:                               100.
"""
MEM = "17179869184"


def test_parse_lsof_addresses(fixture):
    ls = parse_lsof(fixture("lsof_listen.txt"))
    assert Listener("Python", 4242, "*", 5000) in ls
    assert Listener("node", 777, "127.0.0.1", 3000) in ls
    assert Listener("node", 778, "[::1]", 3001) in ls


def test_network_listener_is_medium_and_local_grouped():
    res = check_ports(run=fake_run({"lsof": LSOF_SAMPLE}))
    by = {f.key: f for f in res.findings}
    assert by["port:5000:Python"].severity == "medium"
    assert by["ports:local-only"].severity == "info"
    assert by["port:7000:ControlCe"].severity == "info"
    assert sum(1 for f in res.findings if f.key == "port:49527:rapportd") == 1


def test_ports_command_failure_is_skipped():
    res = check_ports(run=fake_run({}))
    assert res.findings == [] and res.skipped


def test_runaway_postcss_workers_are_high():
    ps = "\n".join(f"{i} 1.0 90000 node /p/.next/dev/build/postcss.js" for i in range(40))
    res = check_performance(run=fake_run({"ps": ps, "vm_stat": VM_OK, "sysctl": MEM}))
    f = next(f for f in res.findings if f.key == "perf:runaway:node postcss.js")
    assert f.severity == "high" and "40 copies" in f.evidence


def test_low_memory_is_medium(fixture):
    free = parse_vm_stat(fixture("vm_stat.txt"), memsize=int(MEM))
    assert 0 < free < 1
    res = check_performance(run=fake_run({"ps": "1 0.0 100 /bin/zsh", "vm_stat": VM_LOW, "sysctl": MEM}))
    assert any(f.title == "Low free memory" and f.severity == "medium" for f in res.findings)


def test_parse_ps_names_scripts():
    procs = parse_ps("12 95.5 2048 /usr/local/bin/python3 /x/main.py --flag\n13 0.0 10 /bin/zsh -l\n")
    assert [(p.pid, p.cpu, p.rss_kb, p.name) for p in procs] == [(12, 95.5, 2048, "python3 main.py"), (13, 0.0, 10, "zsh")]


def test_high_cpu_is_low_severity():
    res = check_performance(run=fake_run({"ps": "12 95.5 2048 /usr/bin/python3 main.py", "vm_stat": VM_OK, "sysctl": MEM}))
    assert any(f.key == "perf:cpu:python3 main.py" and f.severity == "low" for f in res.findings)
