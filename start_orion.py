import argparse
import logging
import sys
import time
from pathlib import Path


def auto_install():
    """Regista ORION no Registry Run key (HKCU) — sem precisar de Admin."""
    import winreg
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)
    script = Path(__file__).resolve()
    cmd = f'"{pythonw}" "{script}" --service --no-install'
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    winreg.SetValueEx(key, "ORIONDaemon", 0, winreg.REG_SZ, cmd)
    winreg.CloseKey(key)
    return True


def is_installed():
    """Verifica se ORION ja esta registado para iniciar automaticamente."""
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        idx = 0
        while True:
            name, _, _ = winreg.EnumValue(key, idx)
            if name == "ORIONDaemon":
                winreg.CloseKey(key)
                return True
            idx += 1
    except OSError:
        pass
    except Exception:
        pass
    return False


def setup_logging():
    log_dir = Path(__file__).resolve().parent / "ORION_SYSTEM" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "orion.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ORION Daemon")
    parser.add_argument("--service", action="store_true", help="Run in background mode")
    parser.add_argument("--no-install", action="store_true", help="Skip auto-install check")
    parser.add_argument("--query", type=str, help="Query the knowledge graph (natural language)")
    parser.add_argument("--kg-stats", action="store_true", help="Show knowledge graph statistics")
    args = parser.parse_args()

    log_file = setup_logging()
    logger = logging.getLogger("orion")

    if not args.no_install and not is_installed():
        logger.info("Primeira execucao — a registar ORION para inicio automatico...")
        try:
            auto_install()
            logger.info("ORION registado com sucesso! Vai iniciar automaticamente ao ligar o PC.")
        except Exception as e:
            logger.warning("Nao foi possivel registar: %s", e)

    from orion.daemon import ORIONDaemon

    daemon = ORIONDaemon()

    if args.kg_stats:
        print(daemon.kg_query.ask("estatisticas do grafo"))
        sys.exit(0)

    if args.query:
        print(daemon.kg_query.ask(args.query))
        sys.exit(0)

    daemon.run_background()

    if args.service:
        logger.info("ORION em execucao (modo servico). Log: %s", log_file)
        try:
            while not daemon.should_stop:
                time.sleep(1)
        except KeyboardInterrupt:
            daemon.stop()
    else:
        daemon.start()
