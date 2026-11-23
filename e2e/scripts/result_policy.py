"""Completion checks shared by the live wrapper and host-side regressions."""


def completion_passed(journal, initial_done, completed, deaths, summary, qp, expected_qp):
    total = len(journal)
    remaining = total - len(initial_done)
    return (total > 0 and remaining > 0 and all([state == 'complete' for state in journal.values()])
            and completed == remaining and deaths == 0 and summary.get('done') == total
            and summary.get('total') == total and summary.get('stuck') == 0
            and (expected_qp == 0 or qp == expected_qp))
