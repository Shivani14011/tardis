import os
import pytest
import numpy as np
import pandas as pd
import tardis.montecarlo.formal_integral as formal_integral
import tardis.montecarlo.montecarlo_numba.r_packet as r_packet
import tardis.montecarlo.montecarlo_configuration as mc
import tardis.montecarlo.montecarlo_numba.numba_interface as numba_interface
from tardis import constants as const
from tardis.montecarlo.montecarlo_numba.numba_interface import Estimators
import tardis.montecarlo.montecarlo_numba.numba_config as numba_config
from tardis.montecarlo.montecarlo_numba import macro_atom
C_SPEED_OF_LIGHT = const.c.to('cm/s').value

from numpy.testing import (
        assert_equal,
        assert_almost_equal,
        assert_array_equal,
        assert_allclose
        )

@pytest.fixture(scope="function")
def packet():
    return r_packet.RPacket(
        r = 7.5e14,
        nu = 0.4,
        mu = 0.3,
        energy = 0.9,
        seed = 1963,
        index = 0,
        is_close_line = 0
    )

@pytest.fixture(scope="function")
def model():
    return numba_interface.NumbaModel(
        r_inner = np.array([6.912e14, 8.64e14], dtype=np.float64),
        r_outer = np.array([8.64e14, 1.0368e15], dtype=np.float64),
        time_explosion = 5.2e7
    )

@pytest.fixture(scope="function")
def estimators():
    return numba_interface.Estimators(
        j_estimator = np.array([0.0, 0.0], dtype=np.float64),
        nu_bar_estimator = np.array([0.0, 0.0], dtype=np.float64),
        j_blue_estimator = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], dtype=np.float64),
        Edotlu_estimator = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    )

@pytest.mark.parametrize(
    ['packet_params', 'expected_params'],
    [({'mu': 0.3, 'r': 7.5e14},
      {'d_boundary': 259376919351035.88}),

     ({'mu': -.3, 'r': 7.5e13},
      {'d_boundary': -664987228972291.5}),

     ({'mu': -.3, 'r': 7.5e14},
      {'d_boundary': 709376919351035.9})]
)
def test_calculate_distance_boundary(packet_params, expected_params, model):
    mu = packet_params['mu']
    r = packet_params['r']

    d_boundary = r_packet.calculate_distance_boundary(
        r, mu, model.r_inner[0], model.r_outer[0])

    #Accuracy to within 0.1cm
    assert_almost_equal(d_boundary[0], expected_params['d_boundary'], decimal=1)
#
#
# TODO: split this into two tests - one to assert errors and other for d_line
@pytest.mark.parametrize(
    ['packet_params', 'expected_params'],
    [({'nu_line': 0.1, 'next_line_id': 0, 'is_last_line': True},
      {'tardis_error': None, 'd_line': 1e+99}),

     ({'nu_line': 0.2, 'next_line_id': 1, 'is_last_line': False},
      {'tardis_error': None, 'd_line': 7.792353908000001e+17}),

     ({'nu_line': 0.5, 'next_line_id': 1, 'is_last_line': False},
      {'tardis_error': r_packet.MonteCarloException, 'd_line': 0.0}),

     ({'nu_line': 0.6, 'next_line_id': 0, 'is_last_line': False},
      {'tardis_error': r_packet.MonteCarloException, 'd_line': 0.0})]
)
def test_calculate_distance_line(packet_params, expected_params, packet, model):
    nu_line = packet_params['nu_line']
    is_last_line = packet_params['is_last_line']

    time_explosion = model.time_explosion

    doppler_factor = r_packet.get_doppler_factor(packet.r,
                                        packet.mu,
                                        time_explosion)
    comov_nu = packet.nu * doppler_factor

    d_line = 0
    obtained_tardis_error = None
    try:
        d_line = r_packet.calculate_distance_line(packet,
                                                    comov_nu,
                                                    is_last_line,
                                                    nu_line,
                                                    time_explosion)
    except r_packet.MonteCarloException:
        obtained_tardis_error = r_packet.MonteCarloException

    assert_almost_equal(d_line, expected_params['d_line'])
    assert obtained_tardis_error == expected_params['tardis_error']

def test_calculate_distance_electron():
    pass

def test_calculate_tau_electron():
    pass

@pytest.mark.parametrize(
    ['mu', 'r', 'inv_t_exp', 'expected'],
    [(0.3, 7.5e14, 1 / 5.2e7, 0.9998556693818854),
     (-.3, 0, 1 / 2.6e7, 1.0),
     (0, 1, 1 / 2.6e7, 1.0)]
)
def test_get_doppler_factor(mu, r, inv_t_exp, expected):
    # Set the params from test cases here
    # TODO: add relativity tests
    time_explosion = 1/inv_t_exp

    # Perform any other setups just before this, they can be additional calls
    # to other methods or introduction of some temporary variables

    obtained = r_packet.get_doppler_factor(r, mu, time_explosion)


    # Perform required assertions
    assert_almost_equal(obtained, expected)

@pytest.mark.parametrize(
    ['mu', 'r', 'inv_t_exp', 'expected'],
    [(0.3, 7.5e14, 1 / 5.2e7, 1/0.9998556693818854),
     (-.3, 0, 1 / 2.6e7, 1.0),
     (0, 1, 1 / 2.6e7, 1.0)]
)
def test_get_inverse_doppler_factor(mu, r, inv_t_exp, expected):
    # Set the params from test cases here
    # TODO: add relativity tests
    time_explosion = 1/inv_t_exp

    # Perform any other setups just before this, they can be additional calls
    # to other methods or introduction of some temporary variables

    obtained = r_packet.get_inverse_doppler_factor(r, mu, time_explosion)

    # Perform required assertions
    assert_almost_equal(obtained, expected)


def test_get_random_mu():
    """
    Ensure that different calls results
    """
    output1 = r_packet.get_random_mu()
    output2 = r_packet.get_random_mu()
    assert output1 != output2


@pytest.mark.parametrize(
    ['cur_line_id', 'distance_trace', 'time_explosion', 
        'expected_j_blue', 
        'expected_Edotlu'],
    [(0, 1e12, 5.2e7, 
    [[2.249673812803061, 0.0, 0.0], [0.0, 0.0, 0.0]], 
    [[2.249673812803061*0.4, 0.0, 1.0], [0.0, 0.0, 1.0]]),
     (0, 0, 5.2e7, 
     [[2.249675256109242, 0.0,  0.0], [0.0, 0.0, 0.0]], 
     [[2.249675256109242*0.4, 0.0, 1.0], [0.0, 0.0, 1.0],]),
     (1, 1e5, 1e10, 
     [[0.0, 0.0, 0.0], [2.249998311331767, 0.0, 0.0]], 
     [[0.0, 0.0, 1.0], [2.249998311331767*0.4, 0.0, 1.0]])]
)
def test_update_line_estimators(estimators, packet, cur_line_id, distance_trace,
                                time_explosion, expected_j_blue, expected_Edotlu):
    r_packet.update_line_estimators(estimators, packet, cur_line_id, distance_trace,
                                    time_explosion)

    assert_allclose(estimators.j_blue_estimator, expected_j_blue)
    assert_allclose(estimators.Edotlu_estimator, expected_Edotlu)

@pytest.mark.xfail(reason='To be implemented')
def test_trace_packet():
    assert False


@pytest.mark.xfail(reason='bug in full relativity')
@pytest.mark.parametrize('ENABLE_FULL_RELATIVITY', [True, False]) 
@pytest.mark.parametrize( 
    ['packet_params', 'expected_params'], 
    [({'nu': 0.4, 'mu': 0.3, 'energy': 0.9, 'r': 7.5e14},
      {'mu': 0.3120599529139568, 'r': 753060422542573.9, 
       'j': 8998701024436.969, 'nubar': 3598960894542.354}), 

     ({'nu': 0.6, 'mu': -.5, 'energy': 0.5, 'r': 8.1e14}, 
      {'mu': -.4906548373534084, 'r': 805046582503149.2, 
       'j': 5001298975563.031, 'nubar': 3001558973156.1387})] 
)
def test_move_r_packet(packet_params, expected_params, packet, model, estimators, ENABLE_FULL_RELATIVITY):
    distance = 1.e13
    packet.nu = packet_params['nu']
    packet.mu = packet_params['mu']
    packet.energy = packet_params['energy']
    packet.r = packet_params['r']

    numba_config.ENABLE_FULL_RELATIVITY = ENABLE_FULL_RELATIVITY
    r_packet.move_r_packet.recompile() # This must be done as move_r_packet was jitted with ENABLE_FULL_RELATIVITY
    doppler_factor = r_packet.get_doppler_factor(
        packet.r, 
        packet.mu, 
        model.time_explosion)

    r_packet.move_r_packet(
        packet, distance, model.time_explosion, estimators)
    
    assert_almost_equal(packet.mu, expected_params['mu'])
    assert_almost_equal(packet.r, expected_params['r'])

    expected_j = expected_params['j']
    expected_nubar = expected_params['nubar']

    if ENABLE_FULL_RELATIVITY:
        expected_j *= doppler_factor
        expected_nubar *= doppler_factor

    numba_config.ENABLE_FULL_RELATIVITY = False
    assert_allclose(estimators.j_estimator[packet.current_shell_id], 
        expected_j, rtol=5e-7)
    assert_allclose(estimators.nu_bar_estimator[packet.current_shell_id],
        expected_nubar, rtol=5e-7)

def test_set_estimators():
    pass

def test_set_estimators_full_relativity():
    pass

def test_line_emission():
    pass

@pytest.mark.parametrize(
    ['current_shell_id', 'delta_shell', 'no_of_shells'],
    [(132, 11, 132),
     (132, 1, 133),
     (132, 2, 133)]
)
def test_move_packet_across_shell_boundary_emitted(packet, current_shell_id,
                                                   delta_shell,
                                                   no_of_shells):
    packet.current_shell_id = current_shell_id
    r_packet.move_packet_across_shell_boundary(packet, delta_shell,
                                      no_of_shells)
    assert packet.status == r_packet.PacketStatus.EMITTED

@pytest.mark.parametrize(
    ['current_shell_id', 'delta_shell', 'no_of_shells'],
    [(132, -133, 132),
     (132, -133, 133),
     (132, -1e9, 133)]
)
def test_move_packet_across_shell_boundary_reabsorbed(packet, current_shell_id,
                                                   delta_shell,
                                                   no_of_shells):
    packet.current_shell_id = current_shell_id
    r_packet.move_packet_across_shell_boundary(packet, delta_shell,
                                      no_of_shells)
    assert packet.status == r_packet.PacketStatus.REABSORBED


@pytest.mark.parametrize(
    ['current_shell_id', 'delta_shell', 'no_of_shells'],
    [(132, -1, 199),
     (132, 0, 132),
     (132, 20, 154)]
)
def test_move_packet_across_shell_boundary_increment(packet, current_shell_id,
                                                   delta_shell,
                                                   no_of_shells):
    packet.current_shell_id = current_shell_id
    r_packet.move_packet_across_shell_boundary(packet, delta_shell,
                                      no_of_shells)
    assert packet.current_shell_id == current_shell_id + delta_shell

#SAYS WE NEED TO FIX/REMOVE PACKET CALC ENERGY BY MOVING DOPPLER FACTOR TO FUNCTION
"""
@pytest.mark.parametrize(
    ['distance_trace', 'time_explosion'],
    [(0, 1),
     (1, 1),
     (1, 1e9)]
)
def test_packet_energy_limit_one(packet, distance_trace, time_explosion):
    initial_energy = packet.energy
    new_energy = r_packet.calc_packet_energy(packet, distance_trace, time_explosion)
    assert_almost_equal(new_energy, initial_energy)
"""
def test_test_for_close_line():
    pass