from scripts.get_weth import get_weth
from scripts.helpful_scripts import FORKED_LOCAL_ENVIRONMENTS, get_account
from brownie import interface, config, network
from web3 import Web3

test_amount = Web3.toWei(0.1, "ether")


def aave_borrow():
    account = get_account()
    erc20_address = config["networks"][network.show_active()]["weth_token"]
    if network.show_active() in FORKED_LOCAL_ENVIRONMENTS:
        get_weth()
    lending_pool = get_lending_pool()
    # must approve sending ERC20 tokens
    tx = approve_erc20(test_amount, lending_pool.address, erc20_address, account)
    tx = lending_pool.deposit(
        erc20_address, test_amount, account.address, 0, {"from": account}
    )
    tx.wait(1)
    print("Token deposited")
    # How much to borrow?
    borrowable_eth, total_debt = get_borrowable_data(lending_pool, account)
    print("Let's borrow!")
    # get the value of DAI in ETH
    dai_eth_price = get_asset_price(
        config["networks"][network.show_active()]["dai_eth_price_feed"]
    )
    # conversion is borrowable_eth / dai_eth_price for how much dai I can borrow
    # multiply by 0.95 to give a buffer for health purposes
    dai_to_borrow = borrowable_eth / dai_eth_price * 0.95
    print(f"You can borrow {dai_to_borrow} DAI")
    # so let's borrow already!
    dai_token_address = config["networks"][network.show_active()]["dai_token"]
    borrow_tx = lending_pool.borrow(
        dai_token_address,
        Web3.toWei(dai_to_borrow, "ether"),
        1,
        0,
        account.address,
        {"from": account},
    )
    borrow_tx.wait(1)
    print(f"You borrowed {dai_to_borrow} DAI")
    get_borrowable_data(lending_pool, account)
    repay_all(dai_to_borrow, lending_pool, account)


def get_lending_pool():
    # LendingPoolAddressesProvider contract
    lending_pool_addresses_provider = interface.ILendingPoolAddressesProvider(
        config["networks"][network.show_active()]["lending_pool_addresses_provider"]
    )
    lending_pool_address = lending_pool_addresses_provider.getLendingPool()
    lending_pool = interface.ILendingPool(lending_pool_address)
    return lending_pool


def approve_erc20(amount, spender, erc20_address, account):
    print("Approving ERC20 token")
    erc20 = interface.IERC20(erc20_address)

    tx = erc20.approve(spender, amount, {"from": account})
    tx.wait(1)
    print(f"{amount} Token approved!")
    return tx


def get_borrowable_data(lending_pool, account):
    (
        total_collateral_eth,
        total_debt_eth,
        available_borrow_eth,
        current_liquidation_threshold,
        ltv,
        health_factor,
    ) = lending_pool.getUserAccountData(account.address)
    total_collateral_eth = Web3.fromWei(total_collateral_eth, "ether")
    total_debt_eth = Web3.fromWei(total_debt_eth, "ether")
    available_borrow_eth = Web3.fromWei(available_borrow_eth, "ether")
    print(f"You have {total_collateral_eth} ETH deposited")
    print(f"You have {total_debt_eth} ETH borrowed")
    print(f"You have {available_borrow_eth} ETH available to borrow")
    return (float(available_borrow_eth), float(total_debt_eth))


def get_asset_price(asset_price_feed_address):
    asset_price_feed = interface.IAggregatorV3(asset_price_feed_address)
    latest_price = asset_price_feed.latestRoundData()[1]  # price is at the 1 index
    converted_price = Web3.fromWei(latest_price, "ether")
    print(f"DAI/ETH price is {converted_price}")
    return float(converted_price)


def repay_all(amount, lending_pool, account):
    dai_token = config["networks"][network.show_active()]["dai_token"]
    approve_erc20(
        Web3.toWei(amount, "ether"),
        lending_pool,
        dai_token,
        account,
    )
    repay_tx = lending_pool.repay(
        dai_token, amount, 1, account.address, {"from": account}
    )
    repay_tx.wait(1)
    print(f"Repayed {amount} DAI from account:{account.address}!")


def main():
    aave_borrow()
