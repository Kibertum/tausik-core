---
slug: obyavlenie-metoda-dlya-taypchekera-v-miksine-pishi-tolko
title: "Объявление метода «для тайпчекера» в миксине пиши ТОЛЬКО под if TYPE_CHECKING — иначе это живой метод, выигрывающий MRO"
type: gotcha
tags:
  - mixin
  - mro
  - python
  - typing
task: transaction-owners-mostly-do-not-check-ownership
edges: []
---

Миксину нужно назвать метод, который живёт в другом миксине или в композитном классе (чтобы mypy не ругался на self.foo()). Объявляй его ИСКЛЮЧИТЕЛЬНО внутри `if TYPE_CHECKING:`. Обычный `def foo(self) -> None: ...` на уровне класса — это НАСТОЯЩИЙ метод с телом `...`, возвращающий None, и он выигрывает MRO у реального, молча превращая его в no-op.

Почему: в смене #221 при выносе BackendTransactionMixin я объявил _checkpoint/_flush_pending_projection обычными `def ... : ...` «просто для типов». Это заменило бы сброс очереди проекций на пустышку — то есть тихо сломало бы git-проекцию на каждом коммите транзакции, и ни один тест на транзакции этого бы не показал, потому что строки в БД правильные. Поймано до первого прогона, но это ТА ЖЕ природа, что и #620 (коллизия приватных имён миксинов): один плоский namespace, победитель определяется порядком баз, ошибки нет.

Как применять: в репозитории уже есть образец — backend_events_chain.BackendEventsChainMixin объявляет _q/_q1/_ex/_ins/begin_tx под `if TYPE_CHECKING:`. Копируй эту форму. Декоратор тоже копируй: объявляя контекстный менеджер, ставь @contextmanager и в заглушке, иначе mypy увидит у композитного класса две несовместимые сигнатуры («Definition in base class X is incompatible with definition in base class Y»). Проверять факт, а не намерение: `SQLiteBackend._checkpoint.__module__` обязан называть модуль, где метод РЕАЛЬНО написан.
