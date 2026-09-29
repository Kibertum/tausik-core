<!-- lang: en -->
### Documented — `/rewind` is not a safety net, and the changing context comes last

Known limitations now state two facts nothing recorded: Claude Code's `/rewind` restores
only edits made by its own file tools, so anything done through the shell is not rolled
back and git is the only safety net; and the changing part of the rules file (session
state, memory tail) sits in one block at the very end so it does not invalidate the
cached prefix. A test holds that order for the generated rules file and this repository.

<!-- lang: ru -->
### Задокументировано — `/rewind` не страховка, а изменчивый контекст стоит последним

В известных ограничениях записаны два факта, которых не было нигде: `/rewind` в Claude
Code откатывает только правки собственными файловыми инструментами, поэтому сделанное
через shell не откатывается и единственная страховка — git; изменчивая часть файла правил
(состояние сессии, хвост памяти) собрана в один блок в самом конце, чтобы не обнулять
закэшированный префикс. Порядок держит тест — для порождённого файла правил и для этого
репозитория.
