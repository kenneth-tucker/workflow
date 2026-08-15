"""
Tests for part_types/step/dump.py.
"""
import itertools

from part_types.step.dump import DumpStep


def make_dump_step(make_part_context, data=None, fake_manager=None):
    if fake_manager is not None and data:
        fake_manager.data.update(data)
    context = make_part_context()
    return DumpStep(context)


class TestDumpStep:
    def test_prints_no_data_message_when_experiment_data_is_empty(self, make_part_context, fake_manager, capsys):
        step = make_dump_step(make_part_context)
        step.run_step()
        captured = capsys.readouterr()
        assert "no data" in captured.out

    def test_prints_keys_sorted(self, make_part_context, fake_manager, capsys):
        # Expect alphabetical sorting within visible and hidden groups, and hidden group at the end.
        visible_names = ['alex', 'alex.a', 'alex.z', 'diego', 'zara1', 'zara2']
        hidden_names = ['_aa', '_ab', '_s3', 'a._s1', 'a._s2', 'a.b._s4', 'a.b.c._s5']
        step = make_dump_step(
            make_part_context,
            data={name: 0 for name in itertools.chain(visible_names, hidden_names)},
            fake_manager=fake_manager,
        )
        step.run_step()
        captured = capsys.readouterr()
        expected_order = itertools.chain(visible_names, ['Hidden', f'{len(hidden_names)} Items'], hidden_names)
        prev = -1
        for i, s in enumerate(expected_order):
            cur = captured.out.find(s)
            assert cur != -1, f"Expected '{s}' to appear in output, but it did not. Output:\n{captured.out}"
            assert cur > prev, f"Expected '{s}' to appear in order, but it did not. Output:\n{captured.out}"
            prev = cur

    def test_flattens_nested_dict_values_using_dot_notation(self, make_part_context, fake_manager, capsys):
        expected_flattened_keys = ['a.b.c', 'a.b.d', 'a.e', 'fred']
        step = make_dump_step(
            make_part_context,
            data={
                'a': {
                    'b': {
                        'c': 1,
                        'd': 2,
                    },
                    'e': 3,
                },
                'fred': 4,
            },
            fake_manager=fake_manager,
        )
        step.run_step()
        captured = capsys.readouterr()
        for key in expected_flattened_keys:
            assert key in captured.out
