#
# spec file for package csp-billing-adapter-microsoft
#
# Copyright (c) 2023 SUSE LLC
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via https://bugs.opensuse.org/
#

%{?!python_module:%define python_module() python-%{**} python3-%{**}}
%global skip_python2 1
%define pythons python3
Name:           csp-billing-adapter-microsoft
Version:        0.1.1
Release:        0
Summary:        Implements Microsoft metering hooks for csp-billing-adapter
License:        Apache-2.0
Group:          Development/Languages/Python
URL:            https://github.com/SUSE-Enceladus/%{name}
Source:         https://files.pythonhosted.org/packages/source/c/%{name}/%{name}-%{version}.tar.gz
BuildRequires:  fdupes
BuildRequires:  python-rpm-macros
BuildRequires:  %{python_module setuptools}
BuildRequires:  %{python_module pluggy}
BuildRequires:  %{python_module csp-billing-adapter}
%if %{with test}
BuildRequires:  %{python_module pytest}
BuildRequires:  %{python_module coverage}
BuildRequires:  %{python_module pytest-cov}
%endif
Requires:       python-setuptools
Requires:       python-pluggy
Requires:       python-csp-billing-adapter
BuildArch:      noarch
%python_subpackages

%description
Provides a plugin for csp-billing-adapter to handle
metering of usage in Microsoft Azure.

%prep
%autosetup -n %{name}-%{version}

%build
%python_build

%install
%python_install
%python_expand %fdupes %{buildroot}%{$python_sitelib}

%check
%if %{with test}
pytest
%endif

%files %{python_files}
%license LICENSE
%doc README.md CONTRIBUTING.md CHANGES.md
%{python_sitelib}/csp_billing_adapter_microsoft
%{python_sitelib}/csp_billing_adapter_microsoft*-info
#%{python_sitelib}/csp_billing_adapter-%{version}*-info

%changelog