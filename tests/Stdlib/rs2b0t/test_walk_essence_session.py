"""rs2b0t's test/event/webwalk/essenceSession.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.
The exit's gate is the core's here (WorldPathFinderTests.cpp), so the last test reads the state the walker sends it."""

from rs2004.traversal import world_state


def _fn1():
    def _fn2():
        essence_session.clear()
    before_each(_fn2)

    def _fn3():
        expect(essence_session.note_entry_from_npc('Aubury')).to_be('aubury')
        expect(essence_session.get_return_id()).to_be('aubury')
        expect(essence_session.note_entry_from_npc('Wizard Cromperty')).to_be('cromperty')
        expect(essence_session.get_return_id()).to_be('cromperty')
        expect(essence_session.note_entry_from_npc('Brimstail')).to_be('brimstail')
    test('noteEntryFromNpc maps wizard names', _fn3)

    def _fn4():
        expect(essence_session.note_entry_from_crossing_label('Aubury → essence mine')).to_be('aubury')
        expect(essence_session.note_entry_from_crossing_label('Distentor → essence mine')).to_be('distentor')
        expect(essence_session.note_entry_from_crossing_label('Spirit tree → Village')).to_be_null()
    test('noteEntryFromCrossingLabel parses specialCrossing labels', _fn4)

    def _fn5():
        expect(essence_session.note_entry_from_transport(Obj({'loc_name': 'Sedridor', 'action': 'Teleport', 'loc_x': 3106, 'loc_z': 9572}))).to_be('sedridor')
        expect(essence_session.note_entry_from_transport(Obj({'loc_name': 'Portal', 'action': 'Use', 'loc_x': 2932, 'loc_z': 4854}))).to_be_null()
        expect(essence_session.get_return_id()).to_be('sedridor')
    test('Teleport transport notes entry; Portal Use does not', _fn5)

    def _fn6():
        essence_session.note_entry('aubury')
        essence_session.set_harness_override('brimstail')
        expect(essence_session.get_return_id()).to_be('brimstail')
        essence_session.clear_harness_override()
        expect(essence_session.get_return_id()).to_be('aubury')
    test('harness override wins over session for live cheat-tele', _fn6)

    def _fn7():
        expect(world_state().get('essence_exit_return')).to_be_undefined()
        essence_session.note_entry('aubury')
        expect(world_state()['essence_exit_return']).to_be('aubury')
    test('session return gates exit requires like live WorldState', _fn7)


describe('EssenceSession (server varp not on wire)', _fn1)


# The session is the VM's, so it's left as a test finds it.
after_each(lambda: essence_session.clear())
