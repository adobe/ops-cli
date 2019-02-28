#!/usr/bin/env bash

function brew_install_if_not_present {
    package=$1
    echo "Installing $package via brew, if not present"
    if brew ls --versions $package >/dev/null; then
        echo "$package is already present. Skipping."
    else
        HOMEBREW_NO_AUTO_UPDATE=1 brew install $package
    fi
}

function brew_install_or_upgrade {
    package=$1
    echo "Installing/upgrading $package via brew"
    if brew ls --versions $package >/dev/null; then
        HOMEBREW_NO_AUTO_UPDATE=1 brew upgrade $package
    else
        HOMEBREW_NO_AUTO_UPDATE=1 brew install $package
    fi
}

echo "Installing prerequisites"

brew update

brew_install_if_not_present terraform
brew_install_or_upgrade wget
brew_install_or_upgrade aws-iam-authenticator
brew_install_or_upgrade kubernetes-helm
brew_install_or_upgrade kubectl
brew_install_or_upgrade jq

helm init --client-only
helm repo update
