---
slug: git-status-slep-k-crlf-konversii-sravnivat-nado-s-blobom-a
title: "git status слеп к CRLF-конверсии; сравнивать надо с блобом, а не с --eol и не с относительным путём"
type: gotcha
tags:
  - crlf
  - git
  - signing
  - supply-chain
  - windows
task: skill-sign-guard-against-converted-worktree
edges: []
---

Три факта, проверенных прогоном, а не чтением:

1) В клоне с core.autocrlf=true git САМ пишет CRLF в рабочее дерево и считает его чистым: 'git status --porcelain' пуст, 'git diff' пуст — он нормализует перед сравнением. Значит status/diff нельзя использовать для детекта конверсии.

2) 'git ls-files --eol' показывает 'i/lf w/crlf' и работает, НО: в дереве, которое сконвертировали руками (а не через checkout), тот же файл отдал 'w/none'. Коды --eol покрывают только EOL-фильтры. Точная и общая проверка — сравнить байты файла с 'git cat-file blob :<path>': она ловит любой clean/smudge-фильтр (ident, LFS), а не только окончания строк.

3) НЕ вычислять путь до файла относительно 'rev-parse --show-toplevel'. На Windows toplevel возвращается длинным путём (C:/Users/[вычеркнуто: local-path]/...), а рабочий каталог может быть в 8.3-форме ([вычеркнуто: local-path]); os.path.relpath между ними даёт мусор, cat-file падает с rc=128. Спрашивать путь у самого git: 'rev-parse --show-prefix' + 'ls-files -z --full-name'. Никакой арифметики путей.

И отдельно: если проверка на отказ git делает 'continue', она превращается в декорацию — молча объявляет дерево чистым. Отслеживаемый файл, по которому cat-file вернул ненулевой код, — это ошибка, а не «нетронутый файл». Ровно на этом я и споткнулся в первой версии supply_eol.py.

Реализовано в scripts/supply_eol.py, подключено к sign_artifact (аварийный выход --allow-eol-drift). Клонирование пинуется в scripts/skill_git.py: -c core.autocrlf=false -c core.eol=lf ПЛЮС запись пина в локальный конфиг клона, иначе следующий 'git pull' перекон+вертирует (симулировать глобальный конфиг можно только через GIT_CONFIG_GLOBAL: '-c' бьёт локальный конфиг и проверяет не то).
