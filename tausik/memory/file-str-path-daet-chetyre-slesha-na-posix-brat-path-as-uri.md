---
slug: file-str-path-daet-chetyre-slesha-na-posix-brat-path-as-uri
title: "'file:///' + str(path) даёт четыре слэша на POSIX; брать Path.as_uri()"
type: gotcha
tags:
  - cross-platform
  - git
  - posix
  - testing
  - windows
task: gitlab-ci-linux-gate
edges: []
---

Склейка 'file:///' + str(path).replace(os.sep, '/') работает только на Windows, где абсолютный путь начинается с буквы диска: 'file:///C:/tmp/x'. На Linux и macOS путь уже начинается со слэша, и получается 'file:////tmp/x' — четыре слэша.

Правильно: Path(p).as_uri(). Он даёт 'file:///C:/tmp/x' на Windows и 'file:///tmp/x' на POSIX.

Ловушка коварна тем, что на Windows обе формы совпадают байт в байт, поэтому тест зелёный и на ревью выглядит безобидно. Найдено в трёх местах (tests/test_supply_eol.py, tests/test_skill_repo_trust.py, tests/test_skill_manager.py) ровно в тот момент, когда я собрал Linux-пайплайн и посмотрел на свои же тесты глазами другой платформы.

Тот же класс, что и весь релиз 1.6.0: код, который не мог упасть там, где его гоняли. Пока прогон шёл только на Windows, такие места накапливались молча.

Побочно: _validate_url в skill_manager намеренно отвергает file:// (supply-chain guard), поэтому тесты клонирования обходят его monkeypatch'ем — обходить надо в тесте, никогда в коде.
