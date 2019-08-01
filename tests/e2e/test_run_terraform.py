import pytest
from ops.ee.run_terraform import TerraformRunner
from common import test_path


@pytest.fixture
def terraform_runner():
    return TerraformRunner("./", "apply", [])


def test_composition_discovery(terraform_runner, test_path):
    compositions = terraform_runner.discover_all_compositions(path=test_path + "/fixtures/data/env=dev/cluster=cluster1")
    sorted_compositions = terraform_runner.get_sorted_compositions(compositions)
    assert "other" not in sorted_compositions
    assert sorted_compositions == ["network", "cluster"]


def test_discover_single_composition(terraform_runner, test_path):
    compositions = terraform_runner.discover_all_compositions(path=test_path + "/fixtures/data/env=dev/cluster=cluster1/composition=network")
    assert compositions == ["network"]


def test_terraform_commands(test_path):
    terraform_runner = TerraformRunner(composition_path="./", terraform_command="apply", terraform_args=["-auto-approve"])
    compositions = terraform_runner.discover_all_compositions(path=test_path + "/fixtures/data/env=dev/cluster=cluster1")
    sorted_compositions = terraform_runner.get_sorted_compositions(compositions)
    assert len(sorted_compositions) == 2
    network = terraform_runner.get_terraform_commands(sorted_compositions[0])
    assert network == ['rm -rf .terraform',
                    'terraform init ./compositions/terraform/network',
                    'terraform apply -auto-approve -var-file="./compositions/terraform/network/variables.tfvars.json" ./compositions/terraform/network'
                    ]

    cluster = terraform_runner.get_terraform_commands(sorted_compositions[1])
    assert cluster == ['rm -rf .terraform',
                    'terraform init ./compositions/terraform/cluster',
                    'terraform apply -auto-approve -var-file="./compositions/terraform/cluster/variables.tfvars.json" ./compositions/terraform/cluster'
                    ]
